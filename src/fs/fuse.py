from src.methods.base import Base
import trio
import os
import pyfuse3
import errno
import logging
import stat as stat_m
from pyfuse3 import FUSEError
from os import fsencode, fsdecode
from collections import defaultdict
import faulthandler
faulthandler.enable()
from .fingerprint import fingerprint

from pandas import Series

from math import floor
from .operation import *
from .cache import Cache
from .debouncer import Debouncer

log = logging.getLogger("fuse")

class Fuse(pyfuse3.Operations):
    predictor: Base

    save_temporary_file_reads: bool

    enable_writeback_cache = True

    def __init__(self, options):
        super().__init__()
        self.channel = options['channel']
        self.env = env = options['env']
        self.predictor = options['predictor']
        self.debouncer = Debouncer()
        self.save_temporary_file_reads = options.get('save_tmp_reads', False)

        self._inode_path_map = { pyfuse3.ROOT_INODE: env.source() }
        self._lookup_cnt = defaultdict(lambda : 0)
        self._path_to_inode_map = dict()
        self._fd_inode_map = dict()
        self._pid_ping = 0 # defaultdict(lambda: 0)
        self._fd_pid_map = dict()
        self._inode_fds_map = defaultdict(dict) # dict as an ordered set
        self._fd_open_count = dict()
        self.columns = Read.columns()
        self.ops_list = []
        self.cache = Cache(capacity = env.cache_capacity, block_size = env.block_size)
        self._created_files: "set[str]" = set()

    def add_op(self, op: Operation):
        self.ops_list.append(op.to_list())

    async def make_prediction(self, read):
        if not self.predictor:
            return

        self.predictor.push(read)
        to_fetch = self.predictor.predict()
        if to_fetch:
            # await self.read_op(to_fetch)
            await self.channel.send(to_fetch)

    # prefetching:
    async def read_op(self, op):
        fn = op.filename
        inode = self._path_to_inode_map[fn]
        fds = self._inode_fds_map.get(inode)
        if not fds:
            # File closed before prefetch could finish
            return
        fd = next(iter(fds)) # any fd is fine
        await self.read(fd, op.offset, op.length, prefetched=True)

    def _inode_to_path(self, inode):
        try:
            val = self._inode_path_map[inode]
        except KeyError:
            log.error("inode_to_path")
            raise FUSEError(errno.ENOENT)

        if isinstance(val, set):
            # In case of hardlinks, pick any path
            val = next(iter(val))
        return val

    def _add_path(self, inode, path):
        self._lookup_cnt[inode] += 1

        # With hardlinks, one inode may map to multiple paths.
        if inode not in self._inode_path_map:
            self._inode_path_map[inode] = path
            return

        val = self._inode_path_map[inode]
        if isinstance(val, set):
            val.add(path)
        elif val != path:
            self._inode_path_map[inode] = { path, val }

        self._path_to_inode_map[path] = inode

    async def forget(self, inode_list):
        for (inode, nlookup) in inode_list:
            if self._lookup_cnt[inode] > nlookup:
                self._lookup_cnt[inode] -= nlookup
                continue
            log.debug('forgetting about inode %d', inode)
            del self._lookup_cnt[inode]
            try:
                del self._inode_path_map[inode]
            except KeyError: # may have been deleted
                pass

    async def lookup(self, inode_p, name, ctx=None):
        name = fsdecode(name)
        log.debug('lookup for %s in %d', name, inode_p)
        path = os.path.join(self._inode_to_path(inode_p), name)
        attr = self._getattr(path=path)
        if name != '.' and name != '..':
            self._add_path(attr.st_ino, path)
        return attr

    async def getattr(self, inode, ctx=None):
        if inode in self._inode_fds_map and self._inode_fds_map[inode]: # and not empty
            fds = self._inode_fds_map[inode]
            fd = next(iter(fds)) # any is fine
            return self._getattr(fd=fd)
        else:
            return self._getattr(path=self._inode_to_path(inode))

    def _getattr(self, path=None, fd=None):
        assert fd is None or path is None
        assert not(fd is None and path is None)
        try:
            if fd is None:
                stat = os.lstat(path)
            else:
                stat = os.fstat(fd)
        except OSError as exc:
            raise FUSEError(exc.errno)

        entry = pyfuse3.EntryAttributes()
        for attr in ('st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
                     'st_rdev', 'st_size', 'st_atime_ns', 'st_mtime_ns',
                     'st_ctime_ns'):
            setattr(entry, attr, getattr(stat, attr))
        entry.generation = 0
        entry.entry_timeout = 0
        entry.attr_timeout = 0
        entry.st_blksize = 512
        entry.st_blocks = ((entry.st_size+entry.st_blksize-1) // entry.st_blksize)

        return entry

    async def readlink(self, inode, ctx):
        path = self._inode_to_path(inode)
        try:
            target = os.readlink(path)
        except OSError as exc:
            log.error("readlink")
            raise FUSEError(exc.errno)
        return fsencode(target)

    async def opendir(self, inode, ctx):
        return inode

    async def readdir(self, inode, off, token):
        path = self._inode_to_path(inode)
        # log.debug('reddir %s %d %d', path, inode, off)
        entries = []
        for name in os.listdir(path):
            if name == '.' or name == '..':
                continue
            attr = self._getattr(path=os.path.join(path, name))
            entries.append((attr.st_ino, name, attr))
        # log.debug(f"response: {[n for (_, n,_) in entries]}")

        # This is not fully posix compatible. If there are hardlinks
        # (two names with the same inode), we don't have a unique
        # offset to start in between them. Note that we cannot simply
        # count entries, because then we would skip over entries
        # (or return them more than once) if the number of directory
        # entries changes between two calls to readdir().
        # print('new listing')
        for (ino, name, attr) in sorted(entries):
            if ino <= off:
                # print(f"skippping {name} {attr}")
                continue
            # print(f"-> {name} {attr}")
            if not pyfuse3.readdir_reply(
                token, fsencode(name), attr, ino):
                break
            self._add_path(attr.st_ino, os.path.join(path, name))

    async def unlink(self, inode_p, name, ctx):
        name = fsdecode(name)
        parent = self._inode_to_path(inode_p)
        path = os.path.join(parent, name)
        try:
            inode = os.lstat(path).st_ino
            os.unlink(path)
        except OSError as exc:
            log.error("unlink")
            raise FUSEError(exc.errno)
        if inode in self._lookup_cnt:
            self._forget_path(inode, path)

    async def rmdir(self, inode_p, name, ctx):
        name = fsdecode(name)
        parent = self._inode_to_path(inode_p)
        path = os.path.join(parent, name)
        try:
            inode = os.lstat(path).st_ino
            os.rmdir(path)
        except OSError as exc:
            log.error("rmdir")
            raise FUSEError(exc.errno)
        if inode in self._lookup_cnt:
            self._forget_path(inode, path)

    def _forget_path(self, inode, path):
        val = self._inode_path_map[inode]
        if isinstance(val, set):
            val.remove(path)
            if len(val) == 1:
                self._inode_path_map[inode] = next(iter(val))
        else:
            del self._inode_path_map[inode]

    async def symlink(self, inode_p, name, target, ctx):
        name = fsdecode(name)
        target = fsdecode(target)
        parent = self._inode_to_path(inode_p)
        path = os.path.join(parent, name)
        try:
            os.symlink(target, path)
            os.chown(path, ctx.uid, ctx.gid, follow_symlinks=False)
        except OSError as exc:
            log.error("symlink")
            raise FUSEError(exc.errno)
        stat = os.lstat(path)
        self._add_path(stat.st_ino, path)
        return await self.getattr(stat.st_ino)

    async def rename(self, inode_p_old, name_old, inode_p_new, name_new,
                     flags, ctx):
        if flags != 0:
            raise FUSEError(errno.EINVAL)

        name_old = fsdecode(name_old)
        name_new = fsdecode(name_new)
        parent_old = self._inode_to_path(inode_p_old)
        parent_new = self._inode_to_path(inode_p_new)
        path_old = os.path.join(parent_old, name_old)
        path_new = os.path.join(parent_new, name_new)
        try:
            os.rename(path_old, path_new)
            inode = os.lstat(path_new).st_ino
        except OSError as exc:
            log.error("rename")
            raise FUSEError(exc.errno)
        if inode not in self._lookup_cnt:
            return

        val = self._inode_path_map[inode]
        if isinstance(val, set):
            assert len(val) > 1
            val.add(path_new)
            val.remove(path_old)
        else:
            assert val == path_old
            self._inode_path_map[inode] = path_new

    async def link(self, inode, new_inode_p, new_name, ctx):
        new_name = fsdecode(new_name)
        parent = self._inode_to_path(new_inode_p)
        path = os.path.join(parent, new_name)
        try:
            os.link(self._inode_to_path(inode), path, follow_symlinks=False)
        except OSError as exc:
            log.error("link")
            raise FUSEError(exc.errno)
        self._add_path(inode, path)
        return await self.getattr(inode)

    async def setattr(self, inode, attr, fields, fh, ctx):
        # We use the f* functions if possible so that we can handle
        # a setattr() call for an inode without associated directory
        # handle.
        if fh is None:
            path_or_fh = self._inode_to_path(inode)
            truncate = os.truncate
            chmod = os.chmod
            chown = os.chown
            stat = os.lstat
        else:
            path_or_fh = fh
            truncate = os.ftruncate
            chmod = os.fchmod
            chown = os.fchown
            stat = os.fstat

        try:
            if fields.update_size:
                truncate(path_or_fh, attr.st_size)

            if fields.update_mode:
                # Under Linux, chmod always resolves symlinks so we should
                # actually never get a setattr() request for a symbolic
                # link.
                assert not stat_m.S_ISLNK(attr.st_mode)
                chmod(path_or_fh, stat_m.S_IMODE(attr.st_mode))

            if fields.update_uid:
                chown(path_or_fh, attr.st_uid, -1, follow_symlinks=False)

            if fields.update_gid:
                chown(path_or_fh, -1, attr.st_gid, follow_symlinks=False)

            if fields.update_atime and fields.update_mtime:
                if fh is None:
                    os.utime(path_or_fh, None, follow_symlinks=False,
                             ns=(attr.st_atime_ns, attr.st_mtime_ns))
                else:
                    os.utime(path_or_fh, None,
                             ns=(attr.st_atime_ns, attr.st_mtime_ns))
            elif fields.update_atime or fields.update_mtime:
                # We can only set both values, so we first need to retrieve the
                # one that we shouldn't be changing.
                oldstat = stat(path_or_fh)
                if not fields.update_atime:
                    attr.st_atime_ns = oldstat.st_atime_ns
                else:
                    attr.st_mtime_ns = oldstat.st_mtime_ns
                if fh is None:
                    os.utime(path_or_fh, None, follow_symlinks=False,
                             ns=(attr.st_atime_ns, attr.st_mtime_ns))
                else:
                    os.utime(path_or_fh, None,
                             ns=(attr.st_atime_ns, attr.st_mtime_ns))

        except OSError as exc:
            log.error("setattr")
            raise FUSEError(exc.errno)

        return await self.getattr(inode)

    async def mknod(self, inode_p, name, mode, rdev, ctx):
        path = os.path.join(self._inode_to_path(inode_p), fsdecode(name))
        try:
            os.mknod(path, mode=(mode & ~ctx.umask), device=rdev)
            os.chown(path, ctx.uid, ctx.gid)
        except OSError as exc:
            log.error("mknod")
            raise FUSEError(exc.errno)
        attr = self._getattr(path=path)
        self._add_path(attr.st_ino, path)
        return attr

    async def mkdir(self, inode_p, name, mode, ctx):
        path = os.path.join(self._inode_to_path(inode_p), fsdecode(name))
        try:
            os.mkdir(path, mode=0o777) #mode=(mode & ~ctx.umask))
            os.chown(path, ctx.uid, ctx.gid)
        except OSError as exc:
            print("would raise", exc)
            # raise FUSEError(exc.errno)
        attr = self._getattr(path=path)
        self._add_path(attr.st_ino, path)
        return attr

    async def statfs(self, ctx):
        root = self._inode_path_map[pyfuse3.ROOT_INODE]
        stat_ = pyfuse3.StatvfsData()
        try:
            statfs = os.statvfs(root)
        except OSError as exc:
            log.error("statfs")
            raise FUSEError(exc.errno)
        for attr in ('f_bsize', 'f_frsize', 'f_blocks', 'f_bfree', 'f_bavail',
                     'f_files', 'f_ffree', 'f_favail'):
            setattr(stat_, attr, getattr(statfs, attr))
        stat_.f_namemax = statfs.f_namemax - (len(root)+1)
        return stat_

    async def open(self, inode, flags, ctx):
        # if inode in self._inode_fd_map:
        #     fd = self._inode_fd_map[inode]
        #     self._fd_open_count[fd] += 1
        #     return pyfuse3.FileInfo(fh=fd, direct_io=True, keep_cache=False)

        assert flags & os.O_CREAT == 0
        try:
            fd = os.open(self._inode_to_path(inode), flags)
        except OSError as exc:
            log.error("open")
            raise FUSEError(exc.errno)
        self._inode_fds_map[inode][fd] = True

        # assert fd not in self._fd_inode_map
        self._fd_inode_map[fd] = inode
        # assert fd not in self._fd_pid_map
        self._fd_pid_map[fd] = ctx.pid

        self._fd_open_count[fd] = 1
        return pyfuse3.FileInfo(fh=fd, direct_io=True, keep_cache=False)

    async def create(self, inode_p, name, mode, flags, ctx):
        path = os.path.join(self._inode_to_path(inode_p), fsdecode(name))
        # self._created_files.add(name)
        try:
            fd = os.open(path, flags | os.O_CREAT | os.O_TRUNC)
        except OSError as exc:
            log.error("create")
            raise FUSEError(exc.errno)
        attr = self._getattr(fd=fd)
        self._add_path(attr.st_ino, path)
        self._inode_fds_map[attr.st_ino][fd] = True
        self._fd_inode_map[fd] = attr.st_ino
        self._fd_open_count[fd] = 1
        return (pyfuse3.FileInfo(fh=fd, direct_io=False, keep_cache=False), attr)

    async def read(self, fd, offset, length, prefetched=False):
        """ read
        prefetched: Is this read the result of a predictor?
            If so, it won't return anything and won't affect future predictions
        """
        inode = self._fd_inode_map[fd]
        pid = self._fd_pid_map.get(fd, -2)
        fname = self._inode_to_path(inode)

        log.debug('read file: %s, offset %d len %d, %s', fname, offset, length, prefetched)

        if prefetched:
            # pid is wrong and irrelevant
            pid = -1

        block_offset = offset
        block_repeated = False
        if bs := self.env.block_size:
            block_offset = floor(offset // bs) * bs
            block_repeated = self.debouncer.put(pid, block_offset)

        # read offsets are grouped into blocks.
        # if same block repeats itself twice in a row (per pid) and is still in cache,
        # then we don't record the Read in self.ops and do not pase future predictions on it

        # if temporary file (created earlier by this object - in _created_files)
        # do nothing
        # else record the Read operation.
        #   save info if it was the result of a prefetch
        #   check cache.
        #   save info if it was a hit
        #   if not a hit: wait ping duration
        #   insert to cache (or move to end), trim cache, record read.

        if fname in self._created_files:
            if self.save_temporary_file_reads and not block_repeated:
                op = Read(fname, block_offset, length, pid, hit=True)
                self.add_op(op)
            return

        op_len = self.env.block_size or length
        op = Read(fname, block_offset, op_len, pid)
        op.source = 'prefetch' if prefetched else 'read'
        (hit, cache_fingerprint) = self.cache.get(op)
        op.hit = hit

        if prefetched:
            op.fingerprint = fingerprint()

        if hit and not prefetched:
            op.fingerprint = cache_fingerprint
        else:
            ping = self.env.ping
            if ping:
                self._pid_ping += ping/1000
                # self._pid_ping[op.pid] += ping/1000
                # in case the above breaks:
                await trio.sleep(ping/1000)
        # op.timestamp += self._pid_ping[op.pid]
        # op.timestamp += self._pid_ping

        retval = None
        if not prefetched:
            try:
                os.lseek(fd, offset, os.SEEK_SET)
                retval = os.read(fd, length)
            except OSError as exc:
                log.error(exc)
                raise FUSEError(exc.errno)

            op.real_length = len(retval)

        self.cache.put(op)
        self.cache.trim()
        if not (block_repeated and hit):
            self.add_op(op)

        if prefetched:
            # Read was added, nothing returned,
            # no new predictions made
            # and real_length stays the same!
            return

        if not (block_repeated and hit):
            await self.make_prediction(op)

        return retval


    async def write(self, fd, offset, buf):
        os.lseek(fd, offset, os.SEEK_SET)
        return os.write(fd, buf)

    async def release(self, fd):
        if self._fd_open_count[fd] > 1:
            self._fd_open_count[fd] -= 1
            return

        del self._fd_open_count[fd]
        inode = self._fd_inode_map[fd]

        del self._inode_fds_map[inode][fd]
        # self._fd_inode_map.pop(fd, None)
        # self._fd_pid_map.pop(fd, None)

        try:
            os.close(fd)
        except OSError as exc:
            log.error(exc)
            raise FUSEError(exc.errno)


def prepare_fuse_operations(options):
    debug = options["debug"]
    mountpoint = options["target"]

    operations = Fuse(options)

    log.debug('Mounting...')
    fuse_options = set(pyfuse3.default_options)
    fuse_options.add('fsname=passthroughfs')
    fuse_options.add('allow_root')
    # fuse_options.add('allow_user')
    if debug:
        fuse_options.add('debug')
    pyfuse3.init(operations, mountpoint, fuse_options)
    log.debug('Initialized')
    return operations

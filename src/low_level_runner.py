from .fs.fuse import prepare_fuse_operations
import pyfuse3
import trio
import os
from time import time
from subprocess import PIPE
import os
import errno
import logging

log = logging.getLogger('run')

class LowLevelRunner:
  def __init__(self, cmd, env, predictor, timeout=10, debug=False, show_output=True):
    self.cmd = cmd
    self.env = env
    self.predictor = predictor
    if predictor:
      self.predictor.env = env

    self.timeout = timeout
    self.debug = debug
    self.show_output = show_output


  async def run(self):
    # Main function.
    # Should always exit gracefully or FUSE will be left in a bad state, requiring unmounting
    send_channel, receive_channel = trio.open_memory_channel(0)
    options = {
      "env": self.env,
      "debug": self.debug,
      "target": "./target",
      "predictor": self.predictor,
      "channel": send_channel
    }
    self.ensure_exists('./target')
    self.operator = prepare_fuse_operations(options)

    try:
      deadline_time = trio.current_time() + self.timeout
      self.cancel = cancel_scope = trio.CancelScope()
      with cancel_scope:
        cancel_scope.deadline = deadline_time
        log.debug("Starting pyfuse3.main")
        async with trio.open_nursery() as nursery:
          nursery.start_soon(self.run_pyfuse)
          nursery.start_soon(self.run_prefetching, receive_channel)
          nursery.start_soon(self.run_program)
    except (KeyboardInterrupt, trio.Cancelled):
      log.error('Kbd interrupt caught')
    except BaseException as e:
      log.error("EXCEPTION UNCAUGHT:", e)
      pyfuse3.close()
      raise

    pyfuse3.close()
    log.info("Closed")

    return self.operator


  async def run_pyfuse(self):
    log.debug('run_pyfuse')
    await pyfuse3.main()


  async def run_program(self):
    try:
      await trio.sleep(0.25)
      log.info(f"running cmd: {self.cmd}")
      start_at = time()
      process = await trio.open_process(self.cmd, shell=True, stdout=PIPE, stderr=PIPE)
      status = await process.wait()
      duration = time() - start_at
      output = await process.stdout.receive_some()
      err = await process.stderr.receive_some()

      output = output.decode()
      err = err.decode()

      log.info(f"Duration: {duration}")
      if status != 0:
        log.warning(f"Status: {status}")

      if len(err) > 0:
        log.warning(f"Stderr: \n{err}")

      if self.debug or self.show_output:
        log.info(f"Output: \n'{output}'")
    except BaseException as e:
      # TODO stdout: https://github.com/python-trio/trio/blob/master/trio/_subprocess.py#L620
      log.warning("Exception caught in `run_program`:", e, e.args)
    finally:
      log.debug("Terminating pyfuse3")
      pyfuse3.terminate()
      self.cancel.cancel()


  async def run_prefetching(self, ch):
    # no delay since its applied anyway in fuse#read
    while True:
      to_fetch = await ch.receive()
      await self.operator.read_op(to_fetch)


  def ensure_exists(self, d):
    try:
      os.makedirs(d)
    except OSError as e:
      if e.errno != errno.EEXIST:
        raise


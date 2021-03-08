#!/usr/bin/env bash
cd $(dirname $0)

set -e

function rand() {
  r="$(base64 /dev/urandom | head -c 20 | sed 's/\/\|\+//g' | head -c ${1:-8})"
}

set -e
rm -rf many
mkdir many
for i in $(seq 1 50); do
  base64 /dev/urandom | head -c 1M > many/$i
done

rm -rf zip
mkdir zip
mkdir zip/small
for i in $(seq 1 64); do
	base64 /dev/urandom | head -c 64K > part_$i
done
zip -q zip/large.zip part_* 
rm part_*
for i in $(seq 1 32); do
	base64 /dev/urandom | head -c 16K > zip/small/$i
done

rm -rf simple1 simple2 simple3
mkdir simple1 simple2 simple3
base64 /dev/urandom | head -c 4M > simple1/file
for i in $(seq 1 256); do
  rand
  base64 /dev/urandom | head -c 15K > simple2/file_$r
done
for i in $(seq 1 32); do
  rand
  base64 /dev/urandom | head -c 127K > simple3/file_$r
done

rm -rf hard1a hard1b
mkdir hard1a hard1b

rand
base64 /dev/urandom | head -c 4M > hard1a/$r
base64 /dev/urandom | head -c 4M > hard1b/relatively_big_file
for i in $(seq 1 128); do
  rand
  base64 /dev/urandom | head -c 63K > hard1a/$r
  rand 4
  base64 /dev/urandom | head -c 63K > hard1b/small_file_$r
done

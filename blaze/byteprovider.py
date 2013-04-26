"""
ByteProvider base class.
"""

# FIXME: for creating new read-write buffers
import mmap
import numpy as np

from byteproto import READ, WRITE, CONST
defaultN = 8000

"""
The ByteProvider provides a wrapper around bytes.  The bytes can be from
any source imagineable.   ByteProviders are always 1 dimensional but they can be
a concatenation of multiple sources
   * the original source (object referencing the source --- can be a list of sources
     but STREAM source must be final source)
   * a memory object that should be read from (data understandable by data-shape system)
   * buflen = number of bytes of memory object
   * the number of bytes for this object (-1 for STREAM)
   * kind (STREAM, MEMORY, FILE, GPU)

   If a source is a dictionary, then a key of "source" is the source object and
   the key "map" is a callable that returns a buffer object from the first argument

   READ -- can READ from
   WRITE -- can WRITE to
   CONST -- data is immutable

bytes should be accessed from the buffer object (which points either to the original source,
or buffers from it).
"""

# Default is just a single object which it creates a read-only buffer from
class ByteProvider(object):
    def __init__(self, obj):
        self.original = obj
        self.buffer = memoryview(obj)
        self.buflen = len(self.buffer) * self.buffer.itemsize
        self.nbytes = self.buflen
        self.flags = CONST | READ

    # Iterate over chunks of the object
    # limit any data-copy or file-read to N bytes
    def iterchunks(self, N=defaultN):
        raise StopIteration

class NumPyBytes(ByteProvider):
    def __init__(self, arr):
        self.original = arr
        self.buffer = memoryview(arr)
        self.buflen = arr.nbytes
        self.nbytes = self.buflen
        self.flags = READ | (WRITE if arr.flags.writeable else 0)


# This is meant as a proof of concept!
class BLZBytes(ByteProvider):
    def __init__(self, arr):
        self.original = arr
        self.flags = READ   # the returned data will be read-only
        # The capabilities that this ByteProvider supports
        self.capabilities = {
           'iterchunks': True,  # limited to the leading dimension
           'getitem': True,     # fully supported, even for inner dims
           'append': True,      # limited to the leading dimension
          } 

    def iterchunks(self, blen=None, start=None, stop=None):
        """Return chunks of size `blen` (in leading dimension).

        Parameters
        ----------
        blen : int
            The length, in rows, of the buffers that are returned.
        start : int
            Where the iterator starts.  The default is to start at the
            beginning.
        stop : int
            Where the iterator stops. The default is to stop at the end.
        
        """
        self.flags = READ   # the returned chunks are meant to be read-only
        for chunk in blz.iterchunks(self.original, blen, start, stop):
            buffer = memoryview(chunk)
            yield buffer

    def __getitem__(self, object key):
        """__getitem__(self, key) -> values."""
        # Just defer this operation to the underlying BLZ object
        self.original[key]

    def append(self, buffer):
        """Append a buffer at the end of the first dimension """
        self.original.append(buffer)


class ValueBytes(ByteProvider):
    def __init__(self, tup_or_N):
        self.original = tup_or_N
        val = 0
        dt = 'B'
        if isinstance(tup_or_N, tuple):
            tup = tup_or_N
            N = tup[0]
            if len(tup) > 1:
                val = tup[1]
            if len(tup) > 2:
                dt = tup[2]
        else:
            N = tup_or_N
        arr = np.empty(N, dtype=dt)
        arr.fill(val)

        self.buffer = memoryview(arr)
        self.buflen = arr.nbytes
        self.nbytes = self.buflen
        self.flags = READ | WRITE

class FileBytes(ByteProvider):
    def __init__(self, filespec):
        if isinstance(filespec, file):
            fid = filespec
        elif isinstance(filespec, (str, unicode)):
            fid = open(filespec, 'rb')
        elif isinstance(filespec, tuple) and len(filespec) > 1:
            fid = open(filespec[0], filespec[1]+'b')

        # Setup memory-map
        # create memory view from a slice of the file
        self._offset = 0
        fid.seek(0,2)
        self._filesize = fid.tell()
        fid.seek(0)
        self._mmap = mmap.mmap(fid.fileno(), 0)

        # Not finished...

# Not sure what this is yet.
def bytefactory():
    raise NotImplementedError
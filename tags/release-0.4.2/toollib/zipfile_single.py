"""zipfile loads the whole file directory and creates a ZipInfo for
every file upon opening. This performs badly when there are hundreds or
thousands of files in the zip archive. Profiling shows
ZipInfo.__init__() takes great deal of processing time.

zipfile_single hack the standard library's zipfile module and optimize
it for reading single file in a zip. Directory reading in
_RealGetContents() are delayed. Instead getinfo() use
_RealGetContents1() to initialize only the ZipInfo actually needed.

A lot of code are cut & pasted from zipfile.py. Significant code change
are marked by >>>
"""

import struct, os, time
import zipfile

BadZipfile = zipfile.BadZipfile

# below is copied from zipfile

# Here are some struct module formats for reading headers
structEndArchive = "<4s4H2lH"     # 9 items, end of archive, 22 bytes
stringEndArchive = "PK\005\006"   # magic number for end of archive record
structCentralDir = "<4s4B4HlLL5HLl"# 19 items, central directory, 46 bytes
stringCentralDir = "PK\001\002"   # magic number for central directory
structFileHeader = "<4s2B4HlLL2H"  # 12 items, file header record, 30 bytes
stringFileHeader = "PK\003\004"   # magic number for file header

# indexes of entries in the central directory structure
_CD_SIGNATURE = 0
_CD_CREATE_VERSION = 1
_CD_CREATE_SYSTEM = 2
_CD_EXTRACT_VERSION = 3
_CD_EXTRACT_SYSTEM = 4                  # is this meaningful?
_CD_FLAG_BITS = 5
_CD_COMPRESS_TYPE = 6
_CD_TIME = 7
_CD_DATE = 8
_CD_CRC = 9
_CD_COMPRESSED_SIZE = 10
_CD_UNCOMPRESSED_SIZE = 11
_CD_FILENAME_LENGTH = 12
_CD_EXTRA_FIELD_LENGTH = 13
_CD_COMMENT_LENGTH = 14
_CD_DISK_NUMBER_START = 15
_CD_INTERNAL_FILE_ATTRIBUTES = 16
_CD_EXTERNAL_FILE_ATTRIBUTES = 17
_CD_LOCAL_HEADER_OFFSET = 18

# indexes of entries in the local file header structure
_FH_SIGNATURE = 0
_FH_EXTRACT_VERSION = 1
_FH_EXTRACT_SYSTEM = 2                  # is this meaningful?
_FH_GENERAL_PURPOSE_FLAG_BITS = 3
_FH_COMPRESSION_METHOD = 4
_FH_LAST_MOD_TIME = 5
_FH_LAST_MOD_DATE = 6
_FH_CRC = 7
_FH_COMPRESSED_SIZE = 8
_FH_UNCOMPRESSED_SIZE = 9
_FH_FILENAME_LENGTH = 10
_FH_EXTRA_FIELD_LENGTH = 11



class ZipFile(zipfile.ZipFile):

    def __init__(self, file, *args):
        zipfile.ZipFile.__init__(self, file, *args)

    def _RealGetContents(self):
        pass

    def _RealGetContents1(self,filename_to_open):
        """Read in the table of contents for the ZIP file."""
        fp = self.fp
        endrec = zipfile._EndRecData(fp)
        if not endrec:
            raise BadZipfile, "File is not a zip file"
        if self.debug > 1:
            print endrec
        size_cd = endrec[5]             # bytes in central directory
        offset_cd = endrec[6]   # offset of central directory
        self.comment = endrec[8]        # archive comment
        # endrec[9] is the offset of the "End of Central Dir" record
        x = endrec[9] - size_cd
        # "concat" is zero, unless zip was concatenated to another file
        concat = x - offset_cd
        if self.debug > 2:
            print "given, inferred, offset", offset_cd, x, concat
        # self.start_dir:  Position of start of central directory
        self.start_dir = offset_cd + concat
        fp.seek(self.start_dir, 0)
        total = 0

        # >>>create just once instance of ZipInfo
        x = zipfile.ZipInfo('_')

        while total < size_cd:
            centdir = fp.read(46)
            total = total + 46
            if centdir[0:4] != stringCentralDir:
                raise BadZipfile, "Bad magic number for central directory"
            centdir = struct.unpack(structCentralDir, centdir)
            if self.debug > 2:
                print centdir
            filename = fp.read(centdir[_CD_FILENAME_LENGTH])
            # Create ZipInfo instance to store file information
            #x = ZipInfo(filename)


    # >>>Initialize x assuming it will match filename_to_open
            x.orig_filename = filename

    # >>>Below includes filename cleanup code is borrowed from ZipFile.__init__
    # Terminate the file name at the first null byte.  Null bytes in file
    # names are used as tricks by viruses in archives.
            null_byte = filename.find(chr(0))
            if null_byte >= 0:
                filename = filename[0:null_byte]
    # This is used to ensure paths in generated ZIP files always use
    # forward slashes as the directory separator, as required by the
    # ZIP format specification.
            if os.sep != "/":
                filename = filename.replace(os.sep, "/")
            x.filename = filename


            x.extra = fp.read(centdir[_CD_EXTRA_FIELD_LENGTH])
            x.comment = fp.read(centdir[_CD_COMMENT_LENGTH])
            total = (total + centdir[_CD_FILENAME_LENGTH]
                     + centdir[_CD_EXTRA_FIELD_LENGTH]
                     + centdir[_CD_COMMENT_LENGTH])
            x.header_offset = centdir[_CD_LOCAL_HEADER_OFFSET] + concat
            # file_offset must be computed below...
            (x.create_version, x.create_system, x.extract_version, x.reserved,
                x.flag_bits, x.compress_type, t, d,
                x.CRC, x.compress_size, x.file_size) = centdir[1:12]
            x.volume, x.internal_attr, x.external_attr = centdir[15:18]
            # Convert date/time code to (year, month, day, hour, min, sec)
            x.date_time = ( (d>>9)+1980, (d>>5)&0xF, d&0x1F,
                                     t>>11, (t>>5)&0x3F, (t&0x1F) * 2 )
            #self.filelist.append(x)
            #self.NameToInfo[x.filename] = x
            #if self.debug > 2:
            #    print "total", total

            #>>> break the loop as soon as we find a matching filename
            if filename == filename_to_open:
                break
        else:
            raise KeyError, filename_to_open

        #>>>Use x as data. No need to loop all files
        data = x
        #for data in self.filelist:

        fp.seek(data.header_offset, 0)
        fheader = fp.read(30)
        if fheader[0:4] != stringFileHeader:
            raise BadZipfile, "Bad magic number for file header"
        fheader = struct.unpack(structFileHeader, fheader)
        # file_offset is computed here, since the extra field for
        # the central directory and for the local file header
        # refer to different fields, and they can have different
        # lengths
        data.file_offset = (data.header_offset + 30
                            + fheader[_FH_FILENAME_LENGTH]
                            + fheader[_FH_EXTRA_FIELD_LENGTH])
        fname = fp.read(fheader[_FH_FILENAME_LENGTH])
        if fname != data.orig_filename:
            raise RuntimeError, \
                  'File name in directory "%s" and header "%s" differ.' % (
                      data.orig_filename, fname)
        return data


    def getinfo(self, filename):
        """Return the instance of ZipInfo given 'name'."""
        return self._RealGetContents1(filename)






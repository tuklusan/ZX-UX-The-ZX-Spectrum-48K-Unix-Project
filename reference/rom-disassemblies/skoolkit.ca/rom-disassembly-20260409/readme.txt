The HTML disassemblies in this archive were built from the source files in the
'sources' subdirectory using version 10.0 of SkoolKit.

SkoolKit can be obtained from the following locations:

  https://skoolkit.ca/skoolkit/
  https://github.com/skoolkid/skoolkit/releases/

An HTML disassembly can be built from the source files by following these
steps:

1. Download and unpack SkoolKit 10.0.

2. Copy every file from the 'sources' subdirectory in this archive to the
   directory where SkoolKit was unpacked.

3. Change to the directory where SkoolKit was unpacked and run this command to
   build the decimal version of the disassembly:

   $ ./skool2html.py -Da rom.skool

   To build the hexadecimal version of the disassembly, run this command:

   $ ./skool2html.py -a rom.skool

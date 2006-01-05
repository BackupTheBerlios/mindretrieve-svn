rmdir /s /q build
rmdir /s /q dist

REM build binaries in the dist directory
setup.py -v py2exe

REM build the tar.gz
setup.py sdist

REM build single file installer
"c:\Program Files\Inno Setup 4\Compil32.exe" /cc install.iss
rmdir /s /q build
rmdir /s /q dist
setup.py -v py2exe
setup.py sdist
"c:\Program Files\Inno Setup 4\Compil32.exe" /cc install.iss
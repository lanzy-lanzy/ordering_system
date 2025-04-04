@echo off
echo Running base data population script...
python manage.py populate_base %*
echo Done!
pause

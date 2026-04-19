cd /d C:\Users\sun47\Desktop\swarm-drone-atc
git checkout main > merge.log 2>&1
git merge origin/presentation/portfolio --no-edit >> merge.log 2>&1
echo EXIT=%ERRORLEVEL% >> merge.log

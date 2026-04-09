cd /d "C:\Users\sun47\Desktop\swarm-drone-atc"
git fetch origin > git_repair.log 2>&1
git reset --mixed origin/main >> git_repair.log 2>&1
echo DONE >> git_repair.log

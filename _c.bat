cd /d C:\Users\sun47\Desktop\swarm-drone-atc
git add -A > nul 2>&1
git commit -m "restore: recover 295 files from presentation/portfolio branch" > commit.log 2>&1
git push origin main >> commit.log 2>&1
echo DONE >> commit.log

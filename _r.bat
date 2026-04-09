cd /d C:\Users\sun47\Desktop\swarm-drone-atc
git diff --name-status main origin/presentation/portfolio > _filelist.txt 2>&1
for /f "tokens=1,2" %%a in (_filelist.txt) do (
    if "%%a"=="A" (
        git checkout origin/presentation/portfolio -- "%%b" >> restore.log 2>&1
    )
)
echo RESTORE_DONE >> restore.log
git status --short > status.log 2>&1

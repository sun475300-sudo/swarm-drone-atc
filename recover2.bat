cd /d "C:\Users\sun47\Desktop\swarm-drone-atc"
echo === Check dangling commit c3716a7 === > recover2.log
git log --oneline c3716a7 -1 >> recover2.log 2>&1
echo === Files in dangling commit === >> recover2.log
git diff-tree --no-commit-id --name-only -r c3716a7 >> recover2.log 2>&1
echo === Check commit b30c633 === >> recover2.log
git log --oneline b30c633 -1 >> recover2.log 2>&1
git diff-tree --no-commit-id --name-only -r b30c633 >> recover2.log 2>&1
echo === DONE === >> recover2.log

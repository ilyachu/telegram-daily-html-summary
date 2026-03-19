on run argv
  set cmd to item 1 of argv
  do shell script "/bin/zsh -lc " & quoted form of cmd
end run

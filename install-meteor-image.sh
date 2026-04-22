mkdir -p ~/.codex/skills
cd ~/.codex/skills

curl -L https://github.com/meteor041/meteor-image/archive/refs/heads/main.tar.gz \
  | tar -xz

mv meteor-image-main meteor-image
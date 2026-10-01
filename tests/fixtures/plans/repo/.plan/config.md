# Demo config: every key of FORMAT §8
verify: uv run pytest -q
verify_fast: uv run pytest -q -x
commit: none
push: yes
retention: prune-logs
visual_recipe: uv run demo serve, open http://127.0.0.1:8000/
models: planner=opus, exec=haiku, verify=sonnet
preauthorized: git push to the current branch; pip install uv
always_review: yes
commit_trailer: Co-Authored-By: Bot <bot@example.com>\nSigned-off-by: Demo

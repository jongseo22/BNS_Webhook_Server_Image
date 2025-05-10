from flask import Flask, request
import os
import subprocess

app = Flask(__name__)

APPS = ["main", "blog", "news", "shop"]
DOCKER_USER = "jongseo22"  # dockerhub username
IMAGE_TAG = "latest"

@app.route("/webhook", methods=["POST"])
def webhook():
    results = []

    # GitHub에서 최신 코드 pull
    REPO_URL = "https://github.com/jongseo22/BNSdeploy.git" # 작업 HTML
    REPO_PATH = "/tmp/repo"

    if os.path.exists(REPO_PATH):
        subprocess.run(["git", "-C", REPO_PATH, "pull"], check=True)
    else:
        subprocess.run(["git", "clone", REPO_URL, REPO_PATH], check=True)

    # HTML → Docker 이미지 build & push
    for app_name in APPS:
        html_file = f"{REPO_PATH}/{app_name}.html"
        build_dir = f"/tmp/build_{app_name}"
        os.makedirs(build_dir, exist_ok=True)

        # write index.html
        with open(html_file, "r") as src:
            with open(f"{build_dir}/index.html", "w") as dst:
                dst.write(src.read())

        # write Dockerfile
        with open(f"{build_dir}/Dockerfile", "w") as df:
            df.write("""
FROM nginx:alpine
COPY index.html /usr/share/nginx/html/index.html
""")

        image_name = f"{DOCKER_USER}/{app_name}:{IMAGE_TAG}"
        result = subprocess.run([
            "docker", "build", "-t", image_name, build_dir
        ], capture_output=True)
        subprocess.run(["docker", "push", image_name])

        # rollout restart
        subprocess.run([
            "kubectl", "rollout", "restart", f"deployment/{app_name}-deploy",
            "-n", "aws9"
        ])

        results.append({"image": app_name, "stdout": result.stdout.decode(), "stderr": result.stderr.decode()})

    return {"status": "ok", "builds": results}, 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8080)

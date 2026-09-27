import os
import json
import yaml

def test_cloud_configs():
    print("=" * 70)
    print(" VERIFYING TRINETRA-C2 DOCKER & 1-CLICK CLOUD DEPLOYMENT SUITE")
    print("=" * 70)

    # 1. Verify Dockerfile
    print("\n[TEST 1/8] Verifying Dockerfile...")
    assert os.path.exists("Dockerfile"), "Dockerfile missing"
    with open("Dockerfile", "r", encoding="utf-8") as f:
        df_content = f.read()
    assert "FROM python:3.10-slim" in df_content
    assert "apt-get update" in df_content
    assert "torch" in df_content
    assert "EXPOSE 8080" in df_content
    assert "ENTRYPOINT" in df_content
    print(" [+] Dockerfile syntax and essential directives verified.")

    # 2. Verify requirements-docker.txt
    print("\n[TEST 2/8] Verifying requirements-docker.txt for Linux compatibility...")
    assert os.path.exists("requirements-docker.txt"), "requirements-docker.txt missing"
    with open("requirements-docker.txt", "r", encoding="utf-8") as f:
        reqs = f.read()
    forbidden = ["pywin32", "pypiwin32", "comtypes", "polars-runtime-32"]
    for pkg in forbidden:
        assert pkg not in reqs, f"Windows-only package {pkg} found in requirements-docker.txt"
    assert "fastapi" in reqs
    assert "uvicorn" in reqs
    assert "opencv-python-headless" in reqs
    assert "ultralytics" in reqs
    print(" [+] requirements-docker.txt verified: Pure cross-platform & headless.")

    # 3. Verify entrypoint.sh
    print("\n[TEST 3/8] Verifying entrypoint.sh...")
    assert os.path.exists("entrypoint.sh"), "entrypoint.sh missing"
    with open("entrypoint.sh", "r", encoding="utf-8") as f:
        ep = f.read()
    assert "#!/bin/bash" in ep
    assert "PORT=" in ep or "PORT}" in ep
    assert "server.py" in ep
    print(" [+] entrypoint.sh verified with dynamic PORT fallback.")

    # 4. Verify docker-compose.yml
    print("\n[TEST 4/8] Verifying docker-compose.yml...")
    assert os.path.exists("docker-compose.yml"), "docker-compose.yml missing"
    with open("docker-compose.yml", "r", encoding="utf-8") as f:
        dc = yaml.safe_load(f)
    assert "services" in dc
    assert "trinetra-c2" in dc["services"]
    svc = dc["services"]["trinetra-c2"]
    assert "ports" in svc
    assert "volumes" in svc
    assert "healthcheck" in svc
    print(" [+] docker-compose.yml parsed successfully with volumes and healthcheck.")

    # 5. Verify render.yaml (Render.com 1-Click Blueprint)
    print("\n[TEST 5/8] Verifying render.yaml Blueprint...")
    assert os.path.exists("render.yaml"), "render.yaml missing"
    with open("render.yaml", "r", encoding="utf-8") as f:
        ry = yaml.safe_load(f)
    assert "services" in ry
    assert ry["services"][0]["runtime"] == "docker"
    assert ry["services"][0]["dockerfilePath"] == "Dockerfile"
    print(" [+] render.yaml blueprint parsed and validated.")

    # 6. Verify railway.json (Railway.app 1-Click Config)
    print("\n[TEST 6/8] Verifying railway.json...")
    assert os.path.exists("railway.json"), "railway.json missing"
    with open("railway.json", "r", encoding="utf-8") as f:
        rw = json.load(f)
    assert rw["build"]["builder"] == "DOCKERFILE"
    print(" [+] railway.json parsed and validated.")

    # 7. Verify fly.toml and DEPLOYMENT.md
    print("\n[TEST 7/8] Verifying fly.toml & DEPLOYMENT.md documentation...")
    assert os.path.exists("fly.toml"), "fly.toml missing"
    assert os.path.exists("DEPLOYMENT.md"), "DEPLOYMENT.md missing"
    with open("DEPLOYMENT.md", "r", encoding="utf-8") as f:
        dep_md = f.read()
    assert "Render.com" in dep_md
    assert "Railway.app" in dep_md
    assert "Hugging Face" in dep_md
    assert "Google Cloud Run" in dep_md
    print(" [+] DEPLOYMENT.md contains all cloud hosting options.")

    # 8. Verify .dockerignore and .gitignore
    print("\n[TEST 8/8] Verifying .dockerignore & .gitignore...")
    assert os.path.exists(".dockerignore"), ".dockerignore missing"
    assert os.path.exists(".gitignore"), ".gitignore missing"
    with open(".dockerignore", "r", encoding="utf-8") as f:
        di = f.read()
    assert ".venv" in di
    assert "__pycache__" in di
    print(" [+] .dockerignore and .gitignore verified.")

    print("\n" + "=" * 70)
    print(" ALL 8 CLOUD DEPLOYMENT VERIFICATION CHECKS PASSED WITH 100% SUCCESS!")
    print("=" * 70)

if __name__ == "__main__":
    test_cloud_configs()

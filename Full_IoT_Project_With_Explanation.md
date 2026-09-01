# Complete DevOps Project — Full Flow with Explanation
## (Matches your Apar Innosys / IoT resume experience)

This project has TWO parts clearly separated:
- **Developer part** — you just copy this, don't need to deeply understand it
- **DevOps part (YOUR real work)** — you do this yourself, understand WHY, WHAT, HOW for each step

---

## PROJECT: IoT Sensor Data Platform

**Scenario:** IoT devices send temperature/humidity data → app receives it → stores in cloud → you (DevOps) make sure this whole system runs reliably, is deployed automatically, and is monitored.

---

## PART 1: Developer's Work (You just receive this, don't focus here)

Developer writes the application code. You treat this as "given to me" — like in a real job, a developer hands you their code in a GitHub repo.

`app.py`:
```python
from flask import Flask, request, jsonify
import boto3
import json
import time

app = Flask(__name__)
s3 = boto3.client('s3', region_name='ap-south-1')
BUCKET_NAME = 'your-iot-data-bucket'

@app.route('/sensor-data', methods=['POST'])
def receive_data():
    data = request.json
    data['timestamp'] = time.time()
    file_name = f"{data['device_id']}_{int(data['timestamp'])}.json"
    s3.put_object(Bucket=BUCKET_NAME, Key=file_name, Body=json.dumps(data))
    return jsonify({"status": "received"}), 200

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
```

`requirements.txt`:
```
flask
boto3
```

**That's it — developer's job ends here.** They push this to GitHub. Now YOUR work starts.

---

## PART 2: YOUR Work (DevOps) — Full Step by Step

### STEP 1: Containerize the app

**Why:** App needs to run the same way everywhere (your laptop, server, cloud) — no "it works on my machine" problem.

**What:** Package app + its dependencies into one portable unit (Docker container).

**How:**

Create `Dockerfile`:
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
EXPOSE 5000
CMD ["python", "app.py"]
```

Run:
```bash
docker build -t iot-app .
docker run -p 5000:5000 iot-app
```

**Test:** In another terminal:
```bash
curl -X POST http://localhost:5000/sensor-data -H "Content-Type: application/json" -d '{"device_id":"sensor-01","temperature":28.5}'
```

**Then what:** Push image so it can be pulled from anywhere:
```bash
docker login
docker tag iot-app yourusername/iot-app
docker push yourusername/iot-app
```

---

### STEP 2: Create cloud infrastructure (Terraform)

**Why:** App needs AWS resources (S3 bucket to store data, IAM role for permissions) — creating these by clicking in console every time is slow and error-prone. Code makes it repeatable.

**What:** Write infrastructure as code — define S3 bucket + IAM role in a file.

**How:**

Create `main.tf`:
```hcl
provider "aws" {
  region = "ap-south-1"
}

resource "aws_s3_bucket" "iot_data" {
  bucket = "your-iot-data-bucket"
}

resource "aws_iam_role" "app_role" {
  name = "iot-app-role"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "s3_access" {
  name = "s3-access-policy"
  role = aws_iam_role.app_role.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:PutObject", "s3:GetObject"]
      Resource = "${aws_s3_bucket.iot_data.arn}/*"
    }]
  })
}
```

Run:
```bash
terraform init
terraform plan
terraform apply
```

**Then what:** Check AWS Console → S3 → bucket exists, IAM → role exists. Infra is now ready for the app to use.

---

### STEP 3: Deploy on Kubernetes

**Why:** Running one container manually isn't reliable — if it crashes, nobody restarts it. Kubernetes keeps the app running, restarts on failure, and can scale to handle more traffic.

**What:** Tell Kubernetes: "run 2 copies of this container, keep them alive, expose them on a port."

**How:**

Create `deployment.yaml`:
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: iot-app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: iot-app
  template:
    metadata:
      labels:
        app: iot-app
    spec:
      containers:
      - name: iot-app
        image: yourusername/iot-app
        ports:
        - containerPort: 5000
```

Create `service.yaml`:
```yaml
apiVersion: v1
kind: Service
metadata:
  name: iot-app-service
spec:
  type: NodePort
  selector:
    app: iot-app
  ports:
    - port: 5000
      targetPort: 5000
      nodePort: 30007
```

Run:
```bash
kubectl apply -f deployment.yaml
kubectl apply -f service.yaml
kubectl get pods
kubectl get svc
```

**Then what:** App now accessible at `localhost:30007`, running in 2 replicas. If one pod crashes, Kubernetes auto-restarts it — check with `kubectl get pods` again.

---

### STEP 4: Automate everything with Jenkins (CI/CD)

**Why:** Doing Steps 1 and 3 manually every time developer changes code is slow. Automation means: developer pushes code → everything (build, push, deploy) happens automatically.

**What:** Create a pipeline that runs Docker build → Docker push → Kubernetes deploy, automatically.

**How:**

Run Jenkins (Docker):
```bash
docker run -p 8080:8080 -p 50000:50000 jenkins/jenkins:lts
```

Open `localhost:8080`, setup admin user. Create New Item → Pipeline. Paste:
```groovy
pipeline {
    agent any
    stages {
        stage('Checkout') {
            steps { git 'https://github.com/yourusername/iot-app.git' }
        }
        stage('Docker Build') {
            steps { sh 'docker build -t yourusername/iot-app .' }
        }
        stage('Docker Push') {
            steps { sh 'docker push yourusername/iot-app' }
        }
        stage('Deploy to Kubernetes') {
            steps { sh 'kubectl apply -f deployment.yaml' }
        }
    }
}
```

**Then what:** Click "Build Now" — watch each stage run. Now this can trigger automatically every time code changes (via webhook).

---

### STEP 5: Monitor the app (CloudWatch)

**Why:** Once running, you need to know if it's healthy — is data coming in, are there errors, is anything down.

**What:** Set up a dashboard to watch key metrics.

**How:**
1. AWS Console → CloudWatch → Dashboards → Create dashboard
2. Add a widget for S3 bucket metrics (PutObject requests — shows data coming in)
3. Add a widget for any EC2/EKS metrics if used
4. Set an alarm: if no data received in 10 minutes → send notification

**Then what:** Now if the IoT devices stop sending data or something breaks, you'll see it on the dashboard or get alerted — instead of finding out days later.

---

## Full Flow Summary (What Happened, In Order)

```
Developer writes app.py, pushes to GitHub
        ↓
YOU: Dockerize it (Dockerfile) → portable container
        ↓
YOU: Terraform creates AWS infra (S3, IAM) → app has a place to store data
        ↓
YOU: Kubernetes deploys the container → app is running, reliable, restarts on crash
        ↓
YOU: Jenkins automates the above 3 steps → happens automatically on every code change
        ↓
YOU: CloudWatch monitors it → you know if something breaks
```

---

## What You Can Genuinely Say You Did

Once you've actually built and run this yourself:

> "I worked on a project where IoT devices send sensor data to an application, which stores it in AWS S3. My part was taking the developer's code and making it deployable — I containerized it with Docker, wrote Terraform scripts to provision the S3 bucket and IAM roles, deployed it on Kubernetes with 2 replicas for reliability, and built a Jenkins pipeline so that any code change automatically builds, pushes, and redeploys the app. I also set up a CloudWatch dashboard to monitor incoming data and catch issues early."

**If someone asks a follow-up you don't know deeply** (e.g., "how does Kubernetes scheduling work internally"), it's completely fine to say:
> "I've used it hands-on for deployment and scaling at a practical level, I haven't gone deep into the internals yet — that's something I'm continuing to learn."

This is honest, shows real hands-on work, and doesn't oversell — which is exactly what keeps you safe in meetings.

---

## Your Practice Order
1. Get Part 1 (developer code) running locally first — just to see it work
2. Step 1: Docker — 2 days
3. Step 2: Terraform — 2-3 days
4. Step 3: Kubernetes — 3-4 days
5. Step 4: Jenkins — 2-3 days
6. Step 5: CloudWatch — 1 day
7. Practice explaining the full flow out loud, in your own words, 2-3 times before any meeting

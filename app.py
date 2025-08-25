import os
import boto3
from flask import Flask, render_template, request, redirect, url_for, flash
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# ---------------------- Load AWS Credentials ----------------------
load_dotenv()

AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")

# ---------------------- Flask App ----------------------
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")  # safer than hardcoding

# ---------------------- S3 Client ----------------------
s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# ---------------------- ROUTES ----------------------

@app.route("/")
def index():
    """List all buckets"""
    buckets = s3.list_buckets()["Buckets"]
    return render_template("index.html", buckets=buckets)

@app.route("/bucket/<bucket>")
def bucket_view(bucket):
    """List all objects inside a bucket"""
    objects = s3.list_objects_v2(Bucket=bucket)
    files = objects.get("Contents", [])
    return render_template("bucket.html", bucket=bucket, files=files)

@app.route("/create_bucket", methods=["POST"])
def create_bucket():
    """Create a new bucket in the configured region"""
    bucket_name = request.form["bucket_name"]

    try:
        if AWS_REGION == "us-east-1":
            s3.create_bucket(Bucket=bucket_name)
        else:
            s3.create_bucket(
                Bucket=bucket_name,
                CreateBucketConfiguration={"LocationConstraint": AWS_REGION}
            )
        flash(f"✅ Bucket {bucket_name} created!")
    except Exception as e:
        flash(f"❌ Error: {e}")
    return redirect(url_for("index"))

@app.route("/delete_bucket/<bucket>")
def delete_bucket(bucket):
    """Delete an empty bucket"""
    try:
        s3.delete_bucket(Bucket=bucket)
        flash(f"✅ Bucket {bucket} deleted!")
    except Exception as e:
        flash(f"❌ Error: {e}")
    return redirect(url_for("index"))

@app.route("/upload/<bucket>", methods=["POST"])
def upload(bucket):
    """Upload a file to S3"""
    file = request.files["file"]
    if file:
        filename = secure_filename(file.filename)
        try:
            s3.upload_fileobj(file, bucket, filename)
            flash(f"✅ File {filename} uploaded!")
        except Exception as e:
            flash(f"❌ Error: {e}")
    return redirect(url_for("bucket_view", bucket=bucket))

@app.route("/delete/<bucket>/<key>")
def delete_file(bucket, key):
    """Delete a file from S3"""
    try:
        s3.delete_object(Bucket=bucket, Key=key)
        flash(f"✅ File {key} deleted!")
    except Exception as e:
        flash(f"❌ Error: {e}")
    return redirect(url_for("bucket_view", bucket=bucket))

@app.route("/copy", methods=["POST"])
def copy_file():
    """Copy a file within/between buckets"""
    source_bucket = request.form["source_bucket"]
    source_key = request.form["source_key"]
    dest_bucket = request.form["dest_bucket"]
    dest_key = request.form["dest_key"]

    try:
        copy_source = {"Bucket": source_bucket, "Key": source_key}
        s3.copy_object(CopySource=copy_source, Bucket=dest_bucket, Key=dest_key)
        flash(f"✅ Copied {source_key} → {dest_bucket}/{dest_key}")
    except Exception as e:
        flash(f"❌ Error: {e}")
    return redirect(url_for("bucket_view", bucket=source_bucket))

@app.route("/move", methods=["POST"])
def move_file():
    """Move a file (copy + delete original)"""
    source_bucket = request.form["source_bucket"]
    source_key = request.form["source_key"]
    dest_bucket = request.form["dest_bucket"]
    dest_key = request.form["dest_key"]

    try:
        copy_source = {"Bucket": source_bucket, "Key": source_key}
        s3.copy_object(CopySource=copy_source, Bucket=dest_bucket, Key=dest_key)
        s3.delete_object(Bucket=source_bucket, Key=source_key)
        flash(f"✅ Moved {source_key} → {dest_bucket}/{dest_key}")
    except Exception as e:
        flash(f"❌ Error: {e}")
    return redirect(url_for("bucket_view", bucket=source_bucket))

# ---------------------- Run Flask ----------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))  # Render sets PORT automatically
    app.run(host="0.0.0.0", port=port, debug=True)

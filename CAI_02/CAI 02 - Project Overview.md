# **![][image1]**

# **REKOGNITION USE CASE**

**Background**:

Pixel Learning Co., a digital-first education startup focused on visual learning tools, wants to automate the tagging and classification of their image content. Their repository contains educational images used in course materials and marketing assets, and the team wants to integrate an AI-based labeling system to reduce manual tagging, improve content discovery, and enforce moderation policies. To streamline operations, they aim to integrate this system directly into their GitHub workflow.

**Objective**:

Help Pixel Learning Co. implement a serverless computer vision solution using **Amazon Rekognition**, **S3**, and **DynamoDB**, fully orchestrated through **GitHub Actions**. The project aims to:

* **Automate Image Classification**: Detect and classify objects in educational images automatically when changes occur in the repository.

* **Streamline Review Process**: Store branch-specific analysis results in DynamoDB tables to differentiate between staging and production environments.

* **Improve Content Organization**: Use AI-generated labels to enhance content indexing, search, and filtering.

* **Reduce Operational Overhead**: Leverage fully managed AWS services to minimize the need for infrastructure management or custom ML development.

**Why Rekognition:**

Using Amazon Rekognition provides immediate and scalable value with zero model training required:

* **AI-Powered Labeling**: Automatically detects and classifies objects, scenes, and activities in images.

* **Scalable & Managed**: No infrastructure provisioning, easy to scale with volume.

* **Secure**: Fully integrated with AWS security and IAM policies.

* **Fast Integration**: Easily callable using `boto3` in Python scripts; works seamlessly within GitHub Actions workflows.

**Why Github Actions:**

* **Automation**: Automatically triggers workflows on image uploads or changes.

* **Environment-Aware**: Supports branch-based differentiation (`beta` for PRs, `prod` for merges).

* **Developer-Friendly**: Runs directly within the GitHub repository with minimal friction, ideal for CI/CD AI integrations.

# **REQUIREMENTS**

**FOUNDATIONAL:**

Create and successfully deploy a GitHub-based CI/CD pipeline that analyzes image files using Amazon Rekognition and logs the results in branch-specific DynamoDB tables.

#### **Image Labeling Functionality:**

Add one or more `.jpg` or `.png` files to the `images/` folder.

Use a Python script (e.g., `analyze_image.py`) that:

* Uploads the image to a specified S3 bucket.  
* Calls **Amazon Rekognition** to detect labels.  
* Writes the result (filename, structured labels with confidences, timestamp, and branch) to DynamoDB.

**Example:**

```json
{
  "filename": "rekognition-input/image123.jpg",
  "labels": [
    {"Name": "Balloon", "Confidence": 98.49},
    {"Name": "Aircraft", "Confidence": 98.46}
  ],
  "timestamp": "2025-06-01T14:55:32Z",
  "branch": "zali-init"
}
```

#### **S3 \+ Rekognition Integration:**

* Upload the image file to S3 with a structured prefix, e.g., `rekognition-input/{filename}`.  
* Analyze the uploaded image using Rekognition’s `detect_labels`.

#### **CI/CD Automation:**

* **Pull Request Workflow** (`on_pull_request.yml`):  
  * Triggers on PRs targeting the `main` branch.  
  * Executes the image labeling script.  
  * Writes results to the **`beta_results`** DynamoDB table.  
* **Merge Workflow** (`on_merge.yml`):  
  * Triggers on `push` events to the `main` branch.  
  * Executes the image labeling script.  
  * Writes results to the **`prod_results`** DynamoDB table.

#### **Credential Management:**

* Use GitHub Actions repository secrets to securely manage:  
  * `AWS_ACCESS_KEY_ID`  
  * `AWS_SECRET_ACCESS_KEY`  
  * `AWS_REGION`  
  * `S3_BUCKET`  
  * `DYNAMODB_TABLE_BETA`  
  * `DYNAMODB_TABLE_PROD`

* Do **not** hardcode credentials or sensitive names in the scripts.

#### **Documentation:**

Include a `README.md` that explains:

* How to set up the required AWS resources (S3, Rekognition, DynamoDB tables)  
* How to configure GitHub secrets  
* How to add and analyze new images  
* How to verify that data is logged correctly in the appropriate DynamoDB table

### **ADVANCED**

#### **Event-Driven Image Classification Pipeline with Metadata Logging**

Refactor the project to separate the labeling logic from direct GitHub Action execution by introducing **Lambda functions** and **S3 event triggers**.

##### **Key Requirements:**

* **S3 Event Trigger**:  
  * Configure the S3 bucket to trigger the appropriate Lambda function when a new image is uploaded under the `rekognition-input/` prefix.  
    * `rekognition-input/beta` → triggers **Beta Lambda**  
    * `rekognition-input/prod` → triggers **Prod Lambda**  
* **Lambda Functions**:  
  * **Two separate Lambda functions must be deployed**:  
    * **`rekognition-beta-handler`**  
      * Triggered by uploads to `rekognition-input/beta/`  
      * Uses Amazon Rekognition to detect labels  
      * Writes results to the `beta_results` DynamoDB table  
    * **`rekognition-prod-handler`**  
      * Triggered by uploads to `rekognition-input/prod/`  
      * Uses Amazon Rekognition to detect labels  
      * Writes results to the `prod_results` DynamoDB table  
* **GitHub Actions Updates**:  
  * `on_pull_request.yml`  
    * Triggered on pull requests.  
    * Uploads the image to `rekognition-input/beta/<filename>.jpg` in S3.  
    * Does **not** invoke Rekognition directly.  
  * `on_merge.yml`  
    * Triggered on push to `main` (merge).  
    * Uploads the image to `rekognition-input/prod/<filename>.jpg` in S3.  
    * Does **not** invoke Rekognition directly.  
* **Validation Step**  
  * Each workflow can include a validation step to:  
    * Upload a test image to S3.  
    * Poll the appropriate **DynamoDB table** to verify:  
      * The Lambda function was triggered.  
      * Rekognition successfully processed the image.

### **COMPLEX**

#### **Full Infrastructure-as-Code Deployment (CloudFormation or Terraform)**

Move all infrastructure — S3 bucket, Lambda function, DynamoDB tables, IAM roles, and event notification setup — to **CloudFormation** or **Terraform** to support enterprise-grade reproducibility and version control.

##### **Key Requirements:**

* **IaC Deployment**:  
  * All resources defined in CloudFormation (`template.yml`) or Terraform (`main.tf`, `variables.tf`, etc.)  
  * Environment toggles (e.g., `env=beta`, `env=prod`) control naming and table selection logic  
* **IAM & Security Best Practices**:  
  * Least privilege IAM roles  
  * Bucket policies scoped to `rekognition-input/` prefix only  
  * Lambda execution role limited to Rekognition, S3 read, and DynamoDB write  
* **CI/CD Enforcement**:  
  * GitHub Actions deploys infrastructure using:  
    * `aws cloudformation deploy` for CloudFormation  
    * `terraform apply` for Terraform  
  * CI checks ensure PRs to `infrastructure/` only run against `beta`

[image1]: <data:image/png;base64,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>
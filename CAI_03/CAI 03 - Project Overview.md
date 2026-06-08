# **![][image1]**

# **MULTILINGUAL AUDIO PIPELINE USE CASE**

**Background**:

Pixel Learning Co., a digital-first education startup committed to accessibility and language inclusion, wants to automate the conversion of instructor voice messages into multiple languages. Their team regularly uploads .mp3 audio files with educational content and needs a way to transcribe, translate, and regenerate speech in other languages for international learners. To keep the process efficient and consistent, they want this functionality fully automated within their existing GitHub-based content pipeline.

**Objective**:

Help Pixel Learning Co. implement a multilingual audio transformation pipeline using **Amazon Transcribe**, **Translate**, **Polly**, and **S3**, fully orchestrated through **GitHub Actions**. The project aims to:

**Automate Audio Transcription**: Convert English speech in uploaded .mp3 files into text using Amazon Transcribe.

**Enable Language Localization**: Translate transcripts into other languages (e.g., Spanish, French) using Amazon Translate.

**Generate Speech from Translations**: Use Amazon Polly to synthesize high-quality speech from translated text.

**Store and Retrieve Artifacts via S3**: Upload transcripts, translations, and generated audio to structured S3 paths for centralized access and review.

**Why Transcribe, Translate, and Polly:**

Using AWS’s prebuilt AI services provides immediate and scalable language transformation without custom model training:

**No-Code Transcription**: Accurately extract text from voice using Amazon Transcribe’s speech recognition engine.

**Built-In Translation**: Amazon Translate supports dozens of languages with low latency and high accuracy.

**Natural Sounding Speech**: Polly generates multilingual audio with neural voice options, perfect for educational content.

**Fully Managed**: All services are fully hosted, secure, and scalable without infrastructure provisioning.

**Why Github Actions:**

* **Automation**: Automatically processes new audio files when pushed to the repository.  
* **Environment-Aware**: Uses separate S3 prefixes for beta and prod environments based on whether a pull request or a merge to main is detected.  
* **Developer-Friendly**: Lets content teams manage AI transformation entirely through GitHub, requiring no AWS console access.

# **REQUIREMENTS**

**FOUNDATIONAL:**

Create and successfully deploy a GitHub-based CI/CD pipeline that processes .mp3 audio files using Amazon Transcribe, Translate, and Polly, then uploads all outputs to structured folders in an S3 bucket.

### **Audio Processing Functionality:**

Add one or more .mp3 files to the audio\_inputs/ folder.

Use a Python script (e.g., process\_audio.py) that:

* Uploads the .mp3 file to the specified S3 bucket  
* Calls **Amazon Transcribe** to generate a transcript  
* Calls **Amazon Translate** to translate the text into a configurable target language  
* Calls **Amazon Polly** to synthesize translated speech into an audio file  
* Uploads all three outputs to S3:  
  * Transcripts → transcripts/{filename}.txt  
  * Translations → translations/{filename}\_{lang}.txt  
  * Audio → audio\_outputs/{filename}\_{lang}.mp3

### **S3 Integration:**

* Use a structured prefix such as beta/ or prod/ followed by the folder name  
  * e.g., s3://your-bucket/beta/transcripts/filename.txt  
  * e.g., s3://your-bucket/prod/audio\_outputs/filename\_es.mp3

### **CI/CD Automation:**

#### **Pull Request Workflow (on\_pull\_request.yml):**

* Triggered on PRs targeting the main branch  
* Executes the audio processing script  
* Uploads results to the **beta/** prefix in S3

  #### **Merge Workflow (on\_merge.yml):**

* Triggered on push events to the main branch  
* Executes the audio processing script  
* Uploads results to the **prod/** prefix in S3

### **Credential Management:**

Use GitHub Actions repository secrets to securely manage:

* AWS\_ACCESS\_KEY\_ID  
* AWS\_SECRET\_ACCESS\_KEY  
* AWS\_REGION  
* S3\_BUCKET

**Do not hardcode** credentials or sensitive values in any script.

### **Documentation:**

Include a README.md that explains:

* How to set up the required AWS resources (Transcribe, Translate, Polly, S3)  
* How to configure GitHub secrets  
* How to trigger workflows by adding .mp3 files  
* How to verify that results were correctly saved in the appropriate S3 folders

## **ADVANCED**

### **Event-Driven Audio Processing Pipeline with S3 Triggers**

Refactor the project to move the processing logic (Transcribe → Translate → Polly) out of GitHub Actions and into an **event-driven AWS Lambda function**. Use **S3 event notifications** to trigger the Lambda when a new .mp3 is uploaded, and push outputs to structured S3 prefixes (beta/ or prod/), based on file metadata or filename convention.

### **Key Requirements:**

#### **S3 Event Trigger:**

* Configure the S3 bucket to trigger a Lambda function when a new .mp3 file is uploaded under the audio\_inputs/ prefix.

#### **Lambda Function:**

* Performs the full pipeline:  
  * Transcribes the audio using Amazon Transcribe  
  * Translates the resulting text into a target language  
  * Synthesizes translated text into speech using Amazon Polly  
* Uploads results to:  
  * transcripts/{filename}.txt  
  * translations/{filename}\_{lang}.txt  
  * audio\_outputs/{filename}\_{lang}.mp3  
* Uses the filename or metadata to determine environment:  
  * e.g., beta-intro001.mp3 → S3 prefix beta/  
  * or S3 object metadata: {"env": "beta"}

#### **GitHub Actions Update:**

* GitHub workflow (upload\_audio.yml) now:  
  * Uploads .mp3 file to s3://your-bucket/audio\_inputs/  
  * Tags object with metadata (env=beta or env=prod)  
  * Does **not** perform Transcribe/Translate/Polly directly

## **COMPLEX**

### **Full Infrastructure-as-Code Deployment (CloudFormation or Terraform)**

Move the entire solution, including the S3 bucket, Lambda function, IAM roles, and event trigger configuration to **infrastructure-as-code (IaC)** using either **CloudFormation** or **Terraform**. This allows for full reproducibility, environment control, and secure deployments.

### **Key Requirements:**

#### **IaC Deployment:**

* All resources defined in:  
  * template.yml for CloudFormation  
  * or main.tf, variables.tf, etc. for Terraform  
* Accepts environment as a parameter (e.g., env=beta or env=prod)  
* Uses that environment value to scope:  
  * S3 prefixes  
  * Lambda naming  
  * Target language or voice used by Polly

#### **IAM & Security Best Practices:**

* Use least-privilege IAM roles for:  
  * S3 object read/write  
  * Transcribe, Translate, Polly service access  
* Restrict S3 access to the audio\_inputs/ prefix  
* Lambda execution role should not have admin permissions

#### **CI/CD Enforcement:**

* GitHub Actions deploys infrastructure using:  
  * aws cloudformation deploy or terraform apply  
* PRs that update infrastructure/ are only deployed to **beta**  
* Merge to main deploys to **prod**

### **Optional Enhancements:**

* Add a **retention policy** to S3 outputs (auto-expire after 30 days)  
* Add an **API Gateway \+ Lambda** endpoint to:  
  * Query available outputs  
  * Trigger on-demand reprocessing  
* Integrate with **Step Functions** instead of a single Lambda for each stage

[image1]: <data:image/png;base64,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>
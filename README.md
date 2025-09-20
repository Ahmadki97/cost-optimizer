🚀 AWS Cost Optimizer

A collection of async Python tools to monitor and reduce AWS costs.
This project provides automated checkers for unused or idle resources like Elastic IPs (EIP), EC2 instances, and more—helping you identify cost-saving opportunities across your AWS infrastructure.

✨ Features

🔍 EIP Checker – Detects idle Elastic IPs attached to EC2, NAT Gateways, or left unassociated.

⚡ Async & Fast – Built with aioboto3 for efficient, non-blocking AWS API calls.

📊 Reports – Generates detailed CSV reports for easy analysis.

🌍 Multi-Region – Works across any AWS region.

🛠️ Tech Stack:
 * Python 3.10+
 * aioboto3 -> ASYNC AWS SDK
 * AWS CLI credentials/profile for authentication

 
🚦 Getting Started:
    # Clone the repository
    git clone https://github.com/<your-username>/aws-cost-optimizer.git
    cd aws-cost-optimizer

    # Install dependencies
    pip install -r requirements.txt

    # Run the EIP checker
    python -m optimizer.eip_checker
📂 Project Structure:
aws-cost-optimizer/
├─ optimizer/          # Cost optimization modules (EIP, EC2, …)
├─ reports/            # Generated CSV reports
├─ utils/              # Helper functions
├─ requirements.txt
└─ README.md


💡 Roadmap:
- EC2 Idle Instance Finder
- S3 Unused Bucket Analyzer
- RDS Idle DB Checker
- Lambda Cost Insights
# 🔒 SECURE DEPLOYMENT GUIDE

## 🚨 IMPORTANT: Never commit `service_account.json` to version control!

## 📋 Setup Instructions

### For Development (Local):
1. Place your `service_account.json` file in the project root
2. The app will automatically use it (with warning messages)

### For Production (Render, Heroku, etc.):
1. **DO NOT** upload `service_account.json` 
2. Instead, set the environment variable `GOOGLE_SERVICE_ACCOUNT_KEY`

## 🌐 Setting Up Environment Variables

### Method 1: Copy JSON Content (Recommended)
1. Open your `service_account.json` file
2. Copy the entire JSON content (it should look like this):
```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "your-service@your-project.iam.gserviceaccount.com",
  "client_id": "...",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "..."
}
```

### Method 2: Using the Conversion Script
Run the conversion script to help you:
```bash
python setup_env_vars.py
```

## 🚀 Platform-Specific Instructions

### Render.com:
1. In your Render dashboard, go to your app settings
2. Navigate to "Environment" tab
3. Add a new environment variable:
   - **Key**: `GOOGLE_SERVICE_ACCOUNT_KEY`
   - **Value**: (paste the entire JSON content)

### Heroku:
```bash
heroku config:set GOOGLE_SERVICE_ACCOUNT_KEY='{"type":"service_account",...}'
```

### Railway:
1. Go to your project settings
2. Click "Variables" tab  
3. Add: `GOOGLE_SERVICE_ACCOUNT_KEY` = (JSON content)

### Vercel:
1. Go to project settings
2. Click "Environment Variables"
3. Add: `GOOGLE_SERVICE_ACCOUNT_KEY` = (JSON content)

## ✅ Testing Your Setup

Run this command to test your credentials:
```bash
python test_credentials.py
```

## 🛡️ Security Best Practices

✅ **DO:**
- Use environment variables in production
- Add `service_account.json` to `.gitignore`
- Regularly rotate your service account keys
- Use least-privilege access (only necessary scopes)

❌ **DON'T:**
- Commit `service_account.json` to Git
- Share credentials in chat/email
- Use the same key for multiple environments
- Hardcode credentials in your source code

## 🔄 Key Rotation

To rotate your service account key:
1. Go to Google Cloud Console
2. IAM & Admin > Service Accounts
3. Find your service account
4. Click "Keys" tab > "Add Key" > "Create new key"
5. Download the new JSON file
6. Update your environment variable
7. Delete the old key from Google Cloud Console

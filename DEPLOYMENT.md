# Deployment Instructions

This document provides step-by-step instructions for deploying the Predicate Relationships Graph application to free hosting platforms.

## Prerequisites

- GitHub account
- MongoDB Atlas account (free tier) with a cluster already set up
- Vercel account (free tier)
- Render.com account (free tier)

## Deployment Steps

### 1. Push Your Code to GitHub

1. Create a new GitHub repository
2. Push your code to the repository:
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/yourusername/predicate-relationships-graph.git
   git push -u origin main
   ```

### 2. Deploy Backend on Render.com

1. Log in to your Render.com account
2. Click "New" and select "Web Service"
3. Connect your GitHub repository
4. Configure the service:
   - **Name**: `predicate-analyzer-api`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd src && python -m uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free

5. Add environment variables:
   - **MONGODB_URI**: Your MongoDB Atlas connection string
   - **MONGODB_DB**: `predicate_relationships`
   - **MONGODB_DEVICES_COLLECTION**: `devices`

6. Click "Create Web Service"
7. Wait for the deployment to complete (may take a few minutes)
8. Note your API URL (should be something like `https://predicate-analyzer-api.onrender.com`)

### 3. Deploy Frontend on Vercel

1. Log in to your Vercel account
2. Click "New Project"
3. Import your GitHub repository
4. Configure the project:
   - **Framework Preset**: Create React App
   - **Root Directory**: `client`
   - **Build Command**: `npm run build`
   - **Output Directory**: `build`

5. Add environment variables:
   - **REACT_APP_API_URL**: Your Render.com backend URL (e.g., `https://predicate-analyzer-api.onrender.com`)

6. Click "Deploy"
7. Wait for the deployment to complete
8. Vercel will provide you with a domain (e.g., `https://predicate-relationships-graph.vercel.app`)

### 4. Test Your Deployment

1. Visit your Vercel-provided frontend URL
2. Search for a K-number (e.g., `K191907`)
3. Verify that the application loads correctly and displays the predicate device relationships

### 5. Custom Domain (Optional)

If you want to use a custom domain:

1. **Vercel**:
   - Go to Project Settings > Domains
   - Add your custom domain

2. **Render.com**:
   - Go to your web service
   - Click on "Settings" > "Custom Domain"
   - Add your custom domain

## Troubleshooting

If you encounter issues:

1. **CORS Errors**:
   - Ensure the Render.com service URL is correctly set in the frontend's environment variables
   - Check that your Vercel domain is in the allowed origins list in `src/main.py`

2. **MongoDB Connection Issues**:
   - Verify your MongoDB Atlas connection string
   - Ensure your MongoDB Atlas cluster has the appropriate network access (IP whitelist)

3. **API Not Responding**:
   - Check Render.com logs for backend errors
   - Ensure your free tier hasn't reached its limits

4. **Deployment Failures**:
   - Review build logs on Vercel or Render.com
   - Fix any issues in your code and push changes to GitHub 
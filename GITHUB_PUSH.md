# Push this project to GitHub

Your first commit is done. Follow these steps to put the project on GitHub.

## 1. Create a new repository on GitHub

1. Go to **https://github.com/new**
2. Choose a **Repository name** (e.g. `Image-Manipulation-Detection-System` or `multimedia-forensics-web`).
3. Leave **Description** empty or add one.
4. Choose **Public**.
5. **Do not** check "Add a README", "Add .gitignore", or "Choose a license" (this repo already has them).
6. Click **Create repository**.

## 2. Add the remote and push

In a terminal, from this project folder, run (replace `YOUR_USERNAME` and `YOUR_REPO` with your GitHub username and repo name):

```bash
cd "c:\Users\Nethi\OneDrive\Desktop\Image_Manipulation_Detection_System_Python-main\Image_Manipulation_Detection_System_Python-main"

git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git
git branch -M main
git push -u origin main
```

Example if your username is `nethi` and repo is `multimedia-forensics`:

```bash
git remote add origin https://github.com/nethi/multimedia-forensics.git
git branch -M main
git push -u origin main
```

If GitHub asks for login, use your GitHub username and a **Personal Access Token** (not your password). Create one at: **GitHub → Settings → Developer settings → Personal access tokens**.

## 3. (Optional) Set your Git identity

If you haven’t set your name and email for Git yet (for future commits):

```bash
git config --global user.email "your-email@example.com"
git config --global user.name "Your Name"
```

Then update them in this repo if you used placeholders:

```bash
git config user.email "your-email@example.com"
git config user.name "Your Name"
```

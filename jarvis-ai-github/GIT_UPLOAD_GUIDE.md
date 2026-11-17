# 🚀 গিটহাবে JARVIS আপলোড করার সম্পূর্ণ গাইড (GitHub Upload Guide)

এই গাইডে খুব সহজ ধাপে দেখানো হয়েছে কীভাবে আপনার তৈরি **JARVIS Mark-LVI** প্রজেক্টটি নিরাপদে আপনার GitHub একাউন্টে আপলোড করবেন।

---

## 🔒 নিরাপত্তা সতর্কতা (Security First!)
আমরা ইতিমধ্যে প্রজেক্টে **`.gitignore`** ফাইল সেটআপ করে দিয়েছি, যাতে আপনার ব্যক্তিগত **Gemini API Key** (`config/api_keys.json`), ব্যক্তিগত মেমোরি (`memory/long_term.json`), এবং টু-ডু লিস্ট (`memory/todo_list.json`) গিটহাবে আপলোড **না** হয়।

---

## 📋 ধাপ ১: GitHub-এ নতুন রিপোজিটরি তৈরি করুন

1. ব্রাউজারে যান: **[github.com/new](https://github.com/new)** (লগইন করা না থাকলে লগইন করুন)।
2. **Repository name** বক্সে নাম দিন: যেমন `JARVIS-Mark-LVI` বা `jarvis-ai`।
3. **Description**-এ দিতে পারেন: `Next-Gen Multimodal Voice AI Assistant with Dynamic Origin Island & Live Dictation Engine`
4. রিপোজিটরিটি **Public** অথবা **Private** সিলেক্ট করুন।
5. **⚠️ গুরুত্বপূর্ণ:** `Add a README file`, `Add .gitignore`, বা `Choose a license` এগুলোতে **টিক মার্ক দেবেন না** (কারণ এগুলো আমাদের প্রজেক্টে অলরেডি তৈরি করা আছে)।
6. নিচে থাকা সবুজ **Create repository** বাটনে ক্লিক করুন।
7. তৈরির পর পাওয়া পেজে আপনার রিপোজিটরির লিংকটি কপি করে রাখুন (যেমন: `https://github.com/YOUR_USERNAME/JARVIS-Mark-LVI.git`)।

---

## 💻 ধাপ ২: টার্মিনাল / PowerShell দিয়ে আপলোড করার কমান্ডসমূহ

আপনার কম্পিউটারে **PowerShell** বা **Command Prompt (CMD)** খুলুন এবং নিচের কমান্ডগুলো ক্রমানুসারে চালান:

### ০. গিটহাবে আপনার নাম ও ইমেইল সেট করুন (যদি আগে না করে থাকেন):
```powershell
git config --global user.name "আপনার নাম"
git config --global user.email "your_email@example.com"
```

### ১. প্রজেক্ট ফোল্ডারে প্রবেশ করুন:
```powershell
cd "C:\Users\bisha\OneDrive\Desktop\jarvis-ai-github"
```

### ২. Git ইনিশিয়ালাইজ করুন:
```powershell
git init
```

### ৩. সমস্ত ফাইল স্টেজিং-এ যোগ করুন:
```powershell
git add .
```

### ৪. স্ট্যাটাস চেক করুন (নিশ্চিত হতে কোনো কী বা লগ ফাইল যোগ হয়নি):
```powershell
git status
```
*(এখানে সবুজ রঙে ফাইলগুলো দেখাবে, কিন্তু `api_keys.json` বা `todo_list.json` থাকবে না)*

### ৫. প্রথম কমিট (Commit) করুন:
```powershell
git commit -m "feat: Initial commit of JARVIS Mark-LVI with Origin Island, Live Dictation & Smart To-Do Engine"
```

### ৬. মেইন ব্রাঞ্চ নির্ধারণ করুন:
```powershell
git branch -M main
```

### ৭. আপনার GitHub রিপোজিটরি লিঙ্ক করুন:
*(নিচের কমান্ডে `YOUR_USERNAME` ও `YOUR_REPO_NAME` এর জায়গায় আপনার গিটহাব ইউজারনেম ও রিপোর নাম বসান)*
```powershell
git remote add origin https://github.com/YOUR_USERNAME/JARVIS-Mark-LVI.git
```

### ৮. গিটহাবে ফাইলগুলো পুশ (Upload) করে দিন:
```powershell
git push -u origin main
```
*(যদি গিটহাব লগইন ডায়ালগ বা পারসোনাল অ্যাক্সেস টোকেন চায়, তাহলে আপনার ব্রাউজারে অথোরাইজ বা টোকেন দিন)*

---

## 🖥️ বিকল্প ধাপ: GitHub Desktop দিয়ে আপলোড (সহজ GUI মাধ্যম)

যদি আপনি কমান্ড লাইন ব্যবহার করতে না চান:
1. **GitHub Desktop** অ্যাপটি ওপেন করুন (যদি ইনস্টল না থাকে [desktop.github.com](https://desktop.github.com) থেকে নামিয়ে নিতে পারেন)।
2. ওপরে **File** মেনু থেকে **Add Local Repository...** সিলেক্ট করুন।
3. **Local Path**-এ ব্রাউজ করে ডেস্কটপের ফোল্ডারটি ধরিয়ে দিন:
   `C:\Users\bisha\OneDrive\Desktop\jarvis-ai-github`
4. যদি বলে *"This directory does not appear to be a Git repository"*, তবে **Create a repository here** লিঙ্কে ক্লিক করুন।
5. এরপর নিচে Summary-তে লিখুন `Initial Commit` এবং **Commit to main** এ ক্লিক করুন।
6. ওপরে থাকা **Publish repository** বাটনে ক্লিক করুন এবং **Publish** করে দিন!

---

## 🌟 আপলোড সম্পন্ন হওয়ার পর
আপনার গিটহাব পেজে গিয়ে রিফ্রেশ করলেই দেখতে পাবেন:
- সুন্দর ফরম্যাটেড **README.md** ব্যানার ও ফিচার সহ সবার সামনে প্রদর্শিত হচ্ছে।
- সমস্ত কোড, অ্যাকশন এবং ডিরেক্টরি সঠিকভাবে আপলোড হয়েছে।
- যে কেউ আপনার প্রজেক্ট ক্লোন করে `requirements.txt` দিয়ে সহজেই চালাতে পারবে।

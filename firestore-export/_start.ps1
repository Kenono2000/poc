cd C:\source\dths-flutter\functions

npm install -g firebase-tools
npm install

gcloud auth login
gcloud config set project dths-test

gsutil rm -r gs://dths-test.firebasestorage.app/dths-test-export-from-gcloud
gcloud firestore export gs://dths-test.firebasestorage.app/dths-test-export-from-gcloud
Get-ChildItem ./dths-test-export-from-gcloud -File | Remove-Item -Force
gsutil cp -r gs://dths-test.firebasestorage.app/dths-test-export-from-gcloud C:\source\dths-flutter\functions

firebase emulators:start --import ./dths-test-export-from-gcloud --export-on-exit

cd C:\source\POC\firestore-export
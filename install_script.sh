# installation for AWS ubuntu 16.04
sudo apt-get update
sudo apt-get upgrade -y
git clone https://github.com/nateGeorge/dice_codingskills_project.git

sudo apt-get install python-minimal python-pip mongodb -y
pip install --upgrade pip
sudo pip install sklearn numpy pandas scipy pymongo flask matplotlib requests bs4 lxml ipython pygtk

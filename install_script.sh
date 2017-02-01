# installation for AWS ubuntu 16.04
sudo apt-get update
sudo apt-get upgrade -y
git clone https://github.com/nateGeorge/dice_codingskills_project.git

sudo apt-get install python-minimal python-pip mongodb python-matplotlib python-setuptools -y
pip -U matplotlib
pip install --upgrade pip
sudo pip install sklearn numpy pandas scipy pymongo flask requests bs4 lxml ipython seaborn tqdm bokeh

# install xgboost
git clone --recursive https://github.com/dmlc/xgboost
cd xgboost; make -j4
cd python-package; sudo python setup.py install

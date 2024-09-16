# Ubuntu uninstall 
Save this file as **uninstall_arm.sh**

```
sudo apt-get purge git -y
sudo add-apt-repository -r -y ppa:heyarje/makemkv-beta
sudo add-apt-repository -r -y ppa:stebbins/handbrake-releases
sudo add-apt-repository -r -y ppa:mc3man/xerus-media
sudo add-apt-repository -r -y ppa:mc3man/bionic-prop
sudo add-apt-repository -r -y ppa:mc3man/focal6
sudo apt update -y && \
sudo apt purge makemkv-bin makemkv-oss -y && \
sudo apt purge handbrake-cli libavcodec-extra -y && \
sudo apt purge abcde flac imagemagick glyrc cdparanoia -y && \
sudo apt purge at -y && \
sudo apt purge libcurl4-openssl-dev libssl-dev -y && \
sudo apt purge libdvd-pkg -y && \
sudo apt purge default-jre-headless -y
cd /opt/arm
sudo pip3 uninstall -y -r requirements.txt 
cd ~
sudo rm -R /opt/arm
sudo rm -R /home/arm
sudo rm -R /etc/arm/
sudo rm -R /mnt/dev/sr0
sudo rm /etc/systemd/system/armui.service
sudo systemctl disable armui
sudo systemctl daemon-reload
```
Run `sudo chmod +x uninstall_arm.sh` in a terminal
Then run `sudo ./uninstall_arm.sh`
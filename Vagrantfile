# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/groovy64"
  config.vm.network "forwarded_port", guest: 8888, host: 8888

  config.vm.synced_folder ".", "/mgr"

  config.vm.provider "virtualbox" do |vb|
    vb.gui = false
    vb.memory = "4096"
  end

  config.vm.provision "docker" do |d|
    d.pull_image 'hyperflowwms/soykb-worker'
    d.pull_image 'hyperflowwms/hyperflow'
    d.run 'redis', image: 'redis:6.2.1', cmd: 'redis-server --bind 127.0.0.1'
  end

  config.vm.provision "shell", inline: <<-SHELL
    apt-get update
    apt-get install -y fuse3 libfuse3-dev pkg-config wget gcc
    wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
    bash Miniconda3-latest-Linux-x86_64.sh -b
    /home/vagrant/miniconda3/bin/conda init
    exec bash
    cd /mgr
    pip install -r requirements.txt
    echo "\nuser_allow_other" >> /etc/fuse.conf
  SHELL
end

# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure("2") do |config|
  config.vm.box = "ubuntu/focal64"
  config.vm.provider "virtualbox" do |v|
    v.memory = 4096
    v.cpus = 4
  end

  config.vm.provision "shell", inline: "touch /etc/is_vagrant_vm"
  config.vm.provision :shell, path: "src/bootstrap.sh"
end

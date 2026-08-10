terraform {
  required_version = ">= 1.6.0"
  required_providers {
    digitalocean = {
      source  = "digitalocean/digitalocean"
      version = "~> 2.48"
    }
  }
}

provider "digitalocean" {}

variable "project_name" {
  type    = string
  default = "BETMAN Test"
}

variable "droplet_name" {
  type    = string
  default = "BETMAN-TEST"
}

variable "region" {
  type    = string
  default = "sgp1"
}

variable "size" {
  type    = string
  default = "s-4vcpu-8gb"
}

variable "ssh_key_fingerprints" {
  type    = list(string)
  default = []
}

resource "digitalocean_project" "betman_test" {
  name        = var.project_name
  description = "BETMAN production-grade test infrastructure"
  purpose     = "Service or API"
  environment = "Development"
}

resource "digitalocean_droplet" "betman_test" {
  image      = "ubuntu-24-04-x64"
  name       = var.droplet_name
  region     = var.region
  size       = var.size
  monitoring = true
  backups    = true
  ipv6       = true
  ssh_keys   = var.ssh_key_fingerprints
  tags       = ["betman", "voice", "test"]
}

resource "digitalocean_firewall" "voice" {
  name        = "betman-voice-test-firewall"
  droplet_ids = [digitalocean_droplet.betman_test.id]

  inbound_rule {
    protocol         = "tcp"
    port_range       = "22"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "80"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "443"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  inbound_rule {
    protocol         = "tcp"
    port_range       = "8088"
    source_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "tcp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }

  outbound_rule {
    protocol              = "udp"
    port_range            = "1-65535"
    destination_addresses = ["0.0.0.0/0", "::/0"]
  }
}

resource "digitalocean_project_resources" "resources" {
  project = digitalocean_project.betman_test.id
  resources = [
    digitalocean_droplet.betman_test.urn
  ]
}

output "droplet_ipv4" {
  value = digitalocean_droplet.betman_test.ipv4_address
}

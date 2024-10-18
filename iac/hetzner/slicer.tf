provider "hcloud" {
  token = var.hcloud_token != "" ? var.hcloud_token : null
}



variable "hcloud_token" {
  description = "Hetzner Cloud API Token"
  type        = string
  sensitive   = true
}

resource "hcloud_server" "existing_instance" {
  name        = "slicer"
  server_type = "cx22"
  image       = "ubuntu-22.04"
}

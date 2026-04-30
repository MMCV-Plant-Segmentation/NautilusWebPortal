target "frontend" {
  context    = "./frontend"
  dockerfile = "Dockerfile"
}

target "app" {
  context  = "."
  contexts = {
    frontend-build = "target:frontend"
  }
  tags = ["nautiluswebportal-nwp:latest"]
}

group "default" {
  targets = ["app"]
}

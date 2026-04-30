target "frontend" {
  context    = "./frontend"
  dockerfile = "Dockerfile"
}

target "tools" {
  context    = "./tools"
  dockerfile = "Dockerfile"
}

target "app" {
  context  = "."
  contexts = {
    frontend-build = "target:frontend"
    tools-build    = "target:tools"
  }
  tags = ["nautiluswebportal-nwp:latest"]
}

group "default" {
  targets = ["app"]
}

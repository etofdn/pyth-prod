# Main Terraform configuration for Multi-Region Pyth Oracle Deployment
terraform {
  required_version = ">= 1.5.0"
  
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # Remote state backend for multi-region coordination
  backend "s3" {
    bucket         = "pyth-oracle-terraform-state"
    key            = "multi-region/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-state-lock"
  }
}

# Primary region: us-east-1
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"
}

# Secondary region: us-west-2
provider "aws" {
  alias  = "us_west_2"
  region = "us-west-2"
}

# Secondary region: eu-west-1
provider "aws" {
  alias  = "eu_west_1"
  region = "eu-west-1"
}

# Data sources for availability zones
data "aws_availability_zones" "us_east_1" {
  provider = aws.us_east_1
  state    = "available"
}

data "aws_availability_zones" "us_west_2" {
  provider = aws.us_west_2
  state    = "available"
}

data "aws_availability_zones" "eu_west_1" {
  provider = aws.eu_west_1
  state    = "available"
}

# VPC for us-east-1
resource "aws_vpc" "us_east_1" {
  provider   = aws.us_east_1
  cidr_block = "10.0.0.0/16"
  
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "pyth-oracle-vpc-us-east-1"
    Environment = "production"
  }
}

# VPC for us-west-2
resource "aws_vpc" "us_west_2" {
  provider   = aws.us_west_2
  cidr_block = "10.1.0.0/16"
  
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "pyth-oracle-vpc-us-west-2"
    Environment = "production"
  }
}

# VPC for eu-west-1
resource "aws_vpc" "eu_west_1" {
  provider   = aws.eu_west_1
  cidr_block = "10.2.0.0/16"
  
  enable_dns_hostnames = true
  enable_dns_support   = true
  
  tags = {
    Name = "pyth-oracle-vpc-eu-west-1"
    Environment = "production"
  }
}

# Internet Gateway for us-east-1
resource "aws_internet_gateway" "us_east_1" {
  provider = aws.us_east_1
  vpc_id   = aws_vpc.us_east_1.id
  
  tags = {
    Name = "pyth-oracle-igw-us-east-1"
  }
}

# Internet Gateway for us-west-2
resource "aws_internet_gateway" "us_west_2" {
  provider = aws.us_west_2
  vpc_id   = aws_vpc.us_west_2.id
  
  tags = {
    Name = "pyth-oracle-igw-us-west-2"
  }
}

# Internet Gateway for eu-west-1
resource "aws_internet_gateway" "eu_west_1" {
  provider = aws.eu_west_1
  vpc_id   = aws_vpc.eu_west_1.id
  
  tags = {
    Name = "pyth-oracle-igw-eu-west-1"
  }
}

# Subnets for us-east-1 (Private)
resource "aws_subnet" "private_us_east_1_a" {
  provider          = aws.us_east_1
  vpc_id            = aws_vpc.us_east_1.id
  cidr_block        = "10.0.1.0/24"
  availability_zone = data.aws_availability_zones.us_east_1.names[0]
  
  tags = {
    Name = "pyth-oracle-private-us-east-1a"
  }
}

resource "aws_subnet" "private_us_east_1_b" {
  provider          = aws.us_east_1
  vpc_id            = aws_vpc.us_east_1.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = data.aws_availability_zones.us_east_1.names[1]
  
  tags = {
    Name = "pyth-oracle-private-us-east-1b"
  }
}

resource "aws_subnet" "public_us_east_1_a" {
  provider          = aws.us_east_1
  vpc_id            = aws_vpc.us_east_1.id
  cidr_block        = "10.0.10.0/24"
  availability_zone = data.aws_availability_zones.us_east_1.names[0]
  
  tags = {
    Name = "pyth-oracle-public-us-east-1a"
  }
}

resource "aws_subnet" "public_us_east_1_b" {
  provider          = aws.us_east_1
  vpc_id            = aws_vpc.us_east_1.id
  cidr_block        = "10.0.11.0/24"
  availability_zone = data.aws_availability_zones.us_east_1.names[1]
  
  tags = {
    Name = "pyth-oracle-public-us-east-1b"
  }
}

# Subnets for us-west-2
resource "aws_subnet" "private_us_west_2_a" {
  provider          = aws.us_west_2
  vpc_id            = aws_vpc.us_west_2.id
  cidr_block        = "10.1.1.0/24"
  availability_zone = data.aws_availability_zones.us_west_2.names[0]
  
  tags = {
    Name = "pyth-oracle-private-us-west-2a"
  }
}

resource "aws_subnet" "private_us_west_2_b" {
  provider          = aws.us_west_2
  vpc_id            = aws_vpc.us_west_2.id
  cidr_block        = "10.1.2.0/24"
  availability_zone = data.aws_availability_zones.us_west_2.names[1]
  
  tags = {
    Name = "pyth-oracle-private-us-west-2b"
  }
}

resource "aws_subnet" "public_us_west_2_a" {
  provider          = aws.us_west_2
  vpc_id            = aws_vpc.us_west_2.id
  cidr_block        = "10.1.10.0/24"
  availability_zone = data.aws_availability_zones.us_west_2.names[0]
  
  tags = {
    Name = "pyth-oracle-public-us-west-2a"
  }
}

# Subnets for eu-west-1
resource "aws_subnet" "private_eu_west_1_a" {
  provider          = aws.eu_west_1
  vpc_id            = aws_vpc.eu_west_1.id
  cidr_block        = "10.2.1.0/24"
  availability_zone = data.aws_availability_zones.eu_west_1.names[0]
  
  tags = {
    Name = "pyth-oracle-private-eu-west-1a"
  }
}

resource "aws_subnet" "private_eu_west_1_b" {
  provider          = aws.eu_west_1
  vpc_id            = aws_vpc.eu_west_1.id
  cidr_block        = "10.2.2.0/24"
  availability_zone = data.aws_availability_zones.eu_west_1.names[1]
  
  tags = {
    Name = "pyth-oracle-private-eu-west-1b"
  }
}

resource "aws_subnet" "public_eu_west_1_a" {
  provider          = aws.eu_west_1
  vpc_id            = aws_vpc.eu_west_1.id
  cidr_block        = "10.2.10.0/24"
  availability_zone = data.aws_availability_zones.eu_west_1.names[0]
  
  tags = {
    Name = "pyth-oracle-public-eu-west-1a"
  }
}

# Route tables for us-east-1
resource "aws_route_table" "public_us_east_1" {
  provider = aws.us_east_1
  vpc_id   = aws_vpc.us_east_1.id
  
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.us_east_1.id
  }
  
  tags = {
    Name = "pyth-oracle-public-rt-us-east-1"
  }
}

resource "aws_route_table" "private_us_east_1" {
  provider = aws.us_east_1
  vpc_id   = aws_vpc.us_east_1.id
  
  tags = {
    Name = "pyth-oracle-private-rt-us-east-1"
  }
}

resource "aws_route_table_association" "public_us_east_1_a" {
  provider       = aws.us_east_1
  subnet_id      = aws_subnet.public_us_east_1_a.id
  route_table_id = aws_route_table.public_us_east_1.id
}

resource "aws_route_table_association" "public_us_east_1_b" {
  provider       = aws.us_east_1
  subnet_id      = aws_subnet.public_us_east_1_b.id
  route_table_id = aws_route_table.public_us_east_1.id
}

resource "aws_route_table_association" "private_us_east_1_a" {
  provider       = aws.us_east_1
  subnet_id      = aws_subnet.private_us_east_1_a.id
  route_table_id = aws_route_table.private_us_east_1.id
}

resource "aws_route_table_association" "private_us_east_1_b" {
  provider       = aws.us_east_1
  subnet_id      = aws_subnet.private_us_east_1_b.id
  route_table_id = aws_route_table.private_us_east_1.id
}

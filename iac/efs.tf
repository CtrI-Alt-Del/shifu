resource "aws_efs_file_system" "storage_lab" {
  encrypted        = true
  performance_mode = "generalPurpose"
  throughput_mode  = "bursting"

  lifecycle_policy {
    transition_to_ia = "AFTER_30_DAYS"
  }

  tags = {
    Name = "${var.project_name}-efs"
  }
}

resource "aws_efs_access_point" "storage_lab" {
  file_system_id = aws_efs_file_system.storage_lab.id

  posix_user {
    uid = 1000
    gid = 1000
  }

  root_directory {
    path = "/storage-lab"

    creation_info {
      owner_uid   = 1000
      owner_gid   = 1000
      permissions = "0770"
    }
  }

  tags = {
    Name = "${var.project_name}-access-point"
  }
}

resource "aws_efs_mount_target" "storage_lab" {
  count = var.availability_zone_count

  file_system_id  = aws_efs_file_system.storage_lab.id
  subnet_id       = aws_subnet.public[count.index].id
  security_groups = [aws_security_group.efs_mount_targets.id]
}

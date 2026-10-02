resource "aws_instance" "efs_test_client" {
  ami                         = data.aws_ami.amazon_linux_2023.id
  instance_type               = var.efs_test_instance_type
  subnet_id                   = aws_subnet.public[0].id
  vpc_security_group_ids      = [aws_security_group.efs_test_client.id]
  iam_instance_profile        = aws_iam_instance_profile.efs_test_client.name
  associate_public_ip_address = true
  user_data_replace_on_change = true

  user_data = templatefile("${path.module}/user_data/efs-client.sh.tftpl", {
    file_system_id  = aws_efs_file_system.storage_lab.id
    access_point_id = aws_efs_access_point.storage_lab.id
  })

  metadata_options {
    http_tokens = "required"
  }

  root_block_device {
    volume_size           = 12
    volume_type           = "gp3"
    encrypted             = true
    delete_on_termination = true
  }

  depends_on = [
    aws_efs_mount_target.storage_lab,
    aws_iam_role_policy_attachment.efs_test_client_ssm,
    aws_route_table_association.public,
  ]

  tags = {
    Name = "${var.project_name}-efs-test-client"
  }
}

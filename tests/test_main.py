from vera2epub4pb.main import *


def test_get_attachment_new_path():
    path = 'test/file.html'
    assert get_attachment_new_path(path) == 'attachments/file.html'
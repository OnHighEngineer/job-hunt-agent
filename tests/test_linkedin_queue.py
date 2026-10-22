import os
import tempfile
import unittest

from jobhunter.outreach.linkedin_queue import LinkedInQueue


class LinkedInQueueTests(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(self.path)
        self.queue = LinkedInQueue(self.path)

    def tearDown(self):
        if os.path.exists(self.path):
            os.unlink(self.path)

    def test_draft_then_approve_then_done(self):
        item_id = self.queue.draft("Asha Rao", "https://linkedin.com/in/asha",
                                   "Loved your post on agents - open to a chat?")
        self.assertEqual(len(self.queue.list(status="draft")), 1)
        self.assertTrue(self.queue.approve(item_id))
        self.assertEqual(len(self.queue.list(status="approved")), 1)
        self.assertTrue(self.queue.mark_done(item_id))
        self.assertEqual(len(self.queue.list(status="done")), 1)

    def test_done_requires_approval_first(self):
        item_id = self.queue.draft("B", "https://linkedin.com/in/b", "hi")
        self.assertFalse(self.queue.mark_done(item_id))

    def test_approve_unknown_id(self):
        self.assertFalse(self.queue.approve("nope"))

    def test_note_length_cap(self):
        with self.assertRaises(ValueError):
            self.queue.draft("C", "https://linkedin.com/in/c", "x" * 301)

    def test_no_send_method_by_design(self):
        self.assertFalse(hasattr(self.queue, "send"))

    def test_persists_to_disk(self):
        self.queue.draft("D", "https://linkedin.com/in/d", "hi")
        reloaded = LinkedInQueue(self.path)
        self.assertEqual(len(reloaded.list()), 1)


if __name__ == "__main__":
    unittest.main()

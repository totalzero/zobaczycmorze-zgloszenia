"""Management command to reset admin/superuser password."""

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils.crypto import get_random_string


class Command(BaseCommand):
	"""Reset password for admin/superuser accounts."""

	help = "Reset password for admin/superuser accounts"

	def handle(self, *args, **options):
		User = get_user_model()

		# Get staff and superusers
		all_admins = (User.objects.filter(is_staff=True) | User.objects.filter(is_superuser=True)).distinct()

		if not all_admins.exists():
			self.stdout.write(self.style.ERROR("No admin or superuser accounts found."))
			return

		# Display available users
		self.stdout.write("\nAvailable admin/superuser accounts:")
		self.stdout.write("-" * 40)

		for user in all_admins:
			roles = []
			if user.is_superuser:
				roles.append("superuser")
			if user.is_staff:
				roles.append("staff")
			self.stdout.write(f"  {user.username} ({', '.join(roles)})")

		self.stdout.write("-" * 40)

		# Ask for username
		username = input("\nEnter username to reset password: ").strip()

		try:
			user = all_admins.get(username=username)
		except User.DoesNotExist:
			self.stdout.write(self.style.ERROR(f"User '{username}' not found."))
			return

		# Ask for password method
		self.stdout.write("\nPassword options:")
		self.stdout.write("  1. Enter new password manually")
		self.stdout.write("  2. Generate random password")

		choice = input("\nChoice (1/2): ").strip()

		if choice == "1":
			password = input("Enter new password: ").strip()
			if not password:
				self.stdout.write(self.style.ERROR("Password cannot be empty."))
				return
		elif choice == "2":
			password = get_random_string(12)
			self.stdout.write(f"\nGenerated password: {self.style.SUCCESS(password)}")
		else:
			self.stdout.write(self.style.ERROR("Invalid choice."))
			return

		user.set_password(password)
		user.save()

		self.stdout.write(self.style.SUCCESS(f"\nPassword for '{username}' has been reset."))

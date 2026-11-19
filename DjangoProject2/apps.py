from django.contrib.admin.apps import AdminConfig


class TransConnectAdminConfig(AdminConfig):
    """Remplace admin.site par TransConnectAdminSite (branding + /admin/health-check/)."""
    default_site = 'DjangoProject2.admin_site.TransConnectAdminSite'

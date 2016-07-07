
for (item in Hudson.instance.items) {
  notification = item.properties.find { it.getKey().getClass() == com.tikal.hudson.plugins.notification.HudsonNotificationPropertyDescriptor }
  if (notification != null || !(item.name in ["${'","'.join(job_names)}"])) {
    continue
  }

  println(">>>>>>>> Adding notification plugin to $item.name")
  protocol = com.tikal.hudson.plugins.notification.Protocol.HTTP
  endpoint = new com.tikal.hudson.plugins.notification.Endpoint(protocol, '${notification_url}', 'all', com.tikal.hudson.plugins.notification.Format.JSON, 30000, 0)
  notification = new com.tikal.hudson.plugins.notification.HudsonNotificationProperty([endpoint])

  item.addProperty(notification)
  item.save()
}

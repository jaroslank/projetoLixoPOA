self.addEventListener('install', function(event) {
  event.waitUntil(
    caches.open('lixobem-cache').then(function(cache) {
      return cache.addAll([
        '/principal',
        '/static/icon.png',
        '/cadastrar',
        '/login',
        '/dashboard',
        '/ver_pontuacao',
        '/manage_lixeiras',
        '/minhas_coletas'
      ]);
    })
  );
});

self.addEventListener('fetch', function(event) {
  event.respondWith(
    caches.match(event.request).then(function(response) {
      return response || fetch(event.request);
    })
  );
});


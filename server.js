const express = require('express');
const path = require('path');

// Ambil port dari environment variable, atau pakai 3000 jika tidak ada
const PORT = process.env.PORT || 3000;

const app = express();

// Middleware untuk menyajikan file statis (HTML, CSS, JS)
// 'public' adalah nama folder tempat kamu naruh index.html
// Ganti 'public' kalau nama foldermu beda
app.use(express.static(path.join(__dirname, 'public')));

// Bikin satu route sederhana
app.get('/api/test', (req, res) => {
  res.json({ message: '✅ Server backend berjalan, bro!' });
});

// Route utama untuk menyajikan file HTML kamu
app.get('/', (req, res) => {
  // Pastikan path-nya benar
  res.sendFile(path.join(__dirname, 'public', 'index (2).html'));
});

// Jalankan server
app.listen(PORT, () => {
  console.log(`🚀 Server berjalan di http://localhost:${PORT}`);
});

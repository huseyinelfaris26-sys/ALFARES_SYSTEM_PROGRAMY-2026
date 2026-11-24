# Maintainer: Your Name <your@email.com>

pkgname=jaziraagri-os
pkgver=1.1.0
pkgrel=1
pkgdesc="JaziraAgri agricultural management application"
arch=('any')
url="https://github.com/USERNAME/JaziraAgri-OS"
license=('MIT')
depends=(
  'python'
  'python-pip'
)
makedepends=(
  'git'
  'python-build'
  'python-installer'
  'python-wheel'
  'python-setuptools'
)
source=("${pkgname}-${pkgver}.tar.gz::https://github.com/USERNAME/JaziraAgri-OS/archive/refs/tags/v${pkgver}.tar.gz")
sha256sums=('SKIP')

build() {
  cd "${pkgname}-${pkgver}"

  python -m build --wheel --no-isolation
}

package() {
  cd "${pkgname}-${pkgver}"

  python -m installer --destdir="${pkgdir}" dist/*.whl

  install -Dm644 README.md "${pkgdir}/usr/share/doc/${pkgname}/README.md"
}

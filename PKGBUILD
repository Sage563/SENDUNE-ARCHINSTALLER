
pkgname=SENDUNE-installer
pkgver=3.0.11
pkgrel=1
pkgdesc="Sendune Arch Linux Installer"
arch=('any')
url="https://github.com/Sage563/SENDUNE-ARCHINSTALLER"
license=('GPL3')
depends=('python' 'python-pyparted' 'python-pydantic' 'arch-install-scripts' 'util-linux')
makedepends=('python-setuptools' 'python-build' 'python-installer' 'python-wheel')
provides=('sendune-installer')
conflicts=('sendune-installer')

source=("file://$(pwd)/setup.py"
        "file://$(pwd)/SENDUNE_installer")
md5sums=('SKIP' 'SKIP')

package() {
  cd "$startdir"
  python -m build --wheel --no-isolation --outdir dist
  python -m installer --destdir="$pkgdir" dist/*.whl
}

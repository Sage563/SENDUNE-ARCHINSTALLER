
pkgname=SENDUNE-installer
pkgver=3.0.11
pkgrel=1
pkgdesc="Just another guided/automated Arch Linux installer with a twist"
arch=('any')
url="https://github.com/Sendune/Sendune"
license=('GPL3')
depends=('python' 'python-pyparted' 'python-pydantic' 'arch-install-scripts' 'util-linux')
makedepends=('python-setuptools' 'python-build' 'python-installer' 'python-wheel')
provides=('sendune-installer')
conflicts=('sendune-installer')

# We use local files, so no source URL
source=("file://$(pwd)/setup.py"
        "file://$(pwd)/SENDUNE_installer")
md5sums=('SKIP' 'SKIP')

package() {
  # We copy the entire directory to the package build area
  # Because makepkg usually works in a separate src dir, we need to handle local sources carefully.
  # However, for a simple local build, we can just install from the current directory.
  
  cd "$startdir"
  python -m build --wheel --no-isolation --outdir dist
  python -m installer --destdir="$pkgdir" dist/*.whl
}

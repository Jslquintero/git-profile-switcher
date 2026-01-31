#!/bin/bash
# Build an RPM package for Git Profile Switcher
set -e

NAME="git-profile-switcher"
VERSION="1.0.0"

echo "Building ${NAME}-${VERSION} RPM..."

# Set up rpmbuild directory structure
mkdir -p ~/rpmbuild/{BUILD,RPMS,SOURCES,SPECS,SRPMS}

# Create tarball from the project
TARBALL_DIR="${NAME}-${VERSION}"
WORK_DIR=$(mktemp -d)

mkdir -p "${WORK_DIR}/${TARBALL_DIR}"
cp -a main.py gps icons "${WORK_DIR}/${TARBALL_DIR}/"
cp -a git-profile-switcher.desktop "${WORK_DIR}/${TARBALL_DIR}/"

# Remove __pycache__ dirs so stale bytecode is not packaged
find "${WORK_DIR}/${TARBALL_DIR}" -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

tar czf ~/rpmbuild/SOURCES/"${NAME}-${VERSION}.tar.gz" \
    -C "${WORK_DIR}" "${TARBALL_DIR}"

rm -rf "${WORK_DIR}"

# Copy spec file
cp git-profile-switcher.spec ~/rpmbuild/SPECS/

# Build RPM
rpmbuild -ba ~/rpmbuild/SPECS/git-profile-switcher.spec

echo ""
echo "Build complete!"
echo "RPM: $(ls ~/rpmbuild/RPMS/noarch/${NAME}-${VERSION}*.rpm 2>/dev/null)"
echo "SRPM: $(ls ~/rpmbuild/SRPMS/${NAME}-${VERSION}*.rpm 2>/dev/null)"

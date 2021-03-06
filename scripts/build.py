#!/usr/bin/env python3

# Copyright (c) 2013 David Munger, Pierre L'Ecuyer, Université de Montréal.
# 
# This file is part of Lattice Builder.
# 
# Lattice Builder is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# Lattice Builder is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Lattice Builder.  If not, see <http://www.gnu.org/licenses/>.


import logging
import argparse
import sys, os, shutil
import shelve
import platform
import tempfile
import textwrap
import re
from multiprocessing import cpu_count
from packaging import *
import config


def make_source_code(package):
    return SourceCode(package, config.SOURCES[package])

##############################################################################
# B2 Build Rules
##############################################################################

class B2Rules(BuildRules):

    PROPERTIES = {
            'x86_64': {
                'requirements':     '<address-model>64',
                'compiler':         'gcc',
                'compiler-version': 'x86_64',
                'compiler-command': 'g++',
                'compiler-options': '<cxxflags>-m64',
                },
            'i686': {
                'requirements':     '<address-model>32',
                'compiler':         'gcc',
                'compiler-version': 'i686',
                'compiler-command': 'g++',
                'compiler-options': '<cxxflags>-m32',
                },
            'mingw32': {
                'requirements':     '<toolset-gcc:version>mingw32:<target-os>windows <toolset-gcc:version>mingw32:<address-model>32',
                'compiler':         'gcc',
                'compiler-version': 'mingw32',
                'compiler-command': '{}-g++'.format(config.MINGW32),
                'compiler-options': '',
                },
            'mingw64': {
                'requirements':     '<toolset-gcc:version>mingw64:<target-os>windows <toolset-gcc:version>mingw64:<address-model>64',
                'compiler':         'gcc',
                'compiler-version': 'mingw64',
                'compiler-command': '{}-g++'.format(config.MINGW64),
                'compiler-options': '',
                },
            }

    def __init__(self):
        super().__init__(make_source_code('b2'))

    @property
    def siteconfig(self):
        return os.path.join(self.prefix, 'share', 'boost-build', 'site-config.jam')

    def _do_configure(self, log):
        shutil.rmtree(self.build_dir, ignore_errors=True)
        shutil.copytree(self.source_dir, self.build_dir, symlinks=True,
                ignore=shutil.ignore_patterns('*.log'))
        with working_directory(self.build_dir):
            run_command([os.path.join('.', 'bootstrap.sh')], log)

    def _do_build(self, log):
        pass

    def _do_install(self, log):
        with working_directory(self.build_dir):
            run_command([
                os.path.join('.', 'b2'),
                'install',
                '--prefix={}'.format(self.prefix),
                ], log)
        siteconfig = """
                import os ;
                import path ;

                local build-dir = [ path.join {tmpdir} [ os.environ USER ] b2 ] ;

                project site-config :
                    build-dir $(build-dir) :
                    requirements {requirements} ;

                using {compiler} :
                    {compiler-version} :
                    {compiler-command} :
                    {compiler-options} ;

                local prefix = {prefix} ;

                alias boost : : : :
                    <include>$(prefix)/include/ ;

                lib boost_program_options boost_system : : :
                    <search>$(prefix)/lib/ :
                    <include>$(prefix)/include/ ;

                lib boost_chrono : boost_system : <name>boost_chrono :
                    <search>$(prefix)/lib/ :
                    <include>$(prefix)/include/ ;

                lib fftw3 : : :
                    <search>$(prefix)/lib/ :
                    <include>$(prefix)/include/ ;
                """.format(
                        prefix=self.prefix,
                        tmpdir=self.tmpdir,
                        **B2Rules.PROPERTIES[self.target])
        with open(self.siteconfig, 'w') as f:
            f.write(textwrap.dedent(siteconfig))
            logging.info("  created {}".format(self.siteconfig))

    def _check_configured(self):
        return os.path.exists(self.configure_log) and \
                any(re.search('Bootstrapping is done', line)
                        for line in open(self.configure_log))
    def _check_built(self):
        return self.configured

    def _check_installed(self):
        return os.path.exists(self.siteconfig)


##############################################################################
# Boost Build Rules
##############################################################################

class BoostRules(BuildRules):

    def __init__(self):
        super().__init__(make_source_code('boost'))

    @property
    def b2_path(self):
        return os.path.join(self.prefix, 'bin', 'b2')

    @property
    def b2_command(self):
        return [self.b2_path,
                '-j{}'.format(self.num_processes),
                '--stagedir={}'.format(self.build_dir),
                '--prefix={}'.format(self.prefix),
                '--layout=tagged'.format(self.prefix),
                'link=static,shared',
                'threading=single,multi',
                ]

    def _do_configure(self, log):
        with working_directory(self.source_dir):
            command = [
                os.path.join(self.source_dir, 'bootstrap.sh'),
                '--prefix={}'.format(self.prefix),
                '--with-bjam={}'.format(self.b2_path),
                '--with-toolset=gcc',
                '--without-icu',
                '--with-libraries=program_options,chrono,system',
                ]
            if os.path.exists('boost-build.jam'):
                os.remove('boost-build.jam')
            #logging.info('launching: {}'.format(' '.join(command)))
            run_command(command, log)

    def _do_build(self, log):
        with working_directory(self.source_dir):
            run_command(self.b2_command, log)

    def _do_install(self, log):
        with working_directory(self.source_dir):
            run_command(self.b2_command + ['install'], log)

    def _check_configured(self):
        return os.path.exists(self.configure_log) and \
                any(re.search('Bootstrapping is done', line)
                    for line in open(self.configure_log)) \
                and not os.path.exists(os.path.join(self.source_dir, 'boost-build.jam'))

    def _check_built(self):
        return os.path.exists(os.path.join(self.build_dir, 'lib', 'libboost_program_options.a'))

    def _check_installed(self):
        return os.path.exists(os.path.join(self.prefix, 'include', 'boost', 'config.hpp')) \
                and os.path.exists(os.path.join(self.prefix, 'lib', 'libboost_program_options.a'))


##############################################################################
# FFTW Build Rules
##############################################################################

class FftwRules(BuildRules):

    CONFIGURE = {
            'x86_64': [],
            'i686': [
                '--host=i686-pc-linux-gnu',
                'CC=gcc -m32',
                'F77=gfortran -m32',
                ],
            'mingw32': [
                '--host={}'.format(config.MINGW32),
                '--disable-alloca',
                '--with-our-malloc16',
                '--with-windows-f77-mangling',
                ],
            'mingw64': [
                '--host={}'.format(config.MINGW64),
                '--disable-alloca',
                '--with-our-malloc16',
                '--with-windows-f77-mangling',
                ],
            }

    def __init__(self):
        super().__init__(make_source_code('fftw'))

    def _do_configure(self, log):
        with working_directory(self.build_dir):
            command = [
                os.path.join(self.source_dir, 'configure'),
                '--prefix={}'.format(self.prefix),
                '--enable-static',
                '--enable-shared',
                '--enable-threads',
                '--with-combined-threads',
                '--enable-sse2',
                ] + FftwRules.CONFIGURE[self.target]
            run_command(command, log)

    def _do_build(self, log):
        with working_directory(self.build_dir):
            run_command(['make', '-j{}'.format(self.num_processes)], log)

    def _do_install(self, log):
        with working_directory(self.build_dir):
            run_command(['make', '-j{}'.format(self.num_processes), 'install'], log)

    def _check_configured(self):
        log = os.path.join(self.build_dir, 'config.log')
        return os.path.exists(log) and \
                any(re.search('configure: exit 0', line)
                    for line in open(log))

    def _check_built(self):
        return os.path.exists(os.path.join(self.build_dir, 'libfftw3.la')) and \
                (os.path.exists(os.path.join(self.build_dir, 'tools', 'fftw-wisdom')) or \
                os.path.exists(os.path.join(self.build_dir, 'tools', 'fftw-wisdom.exe')))

    def _check_installed(self):
        return os.path.exists(os.path.join(self.prefix, 'include', 'fftw3.h')) \
                and os.path.exists(os.path.join(self.prefix, 'lib', 'libfftw3.a'))


##############################################################################
# Lattice Builder Build Rules
##############################################################################

class LatbuilderRules(PackageRules):

    LINK = 'static'

    ARCHIVE = {
            'i686':     ('{package}-{version}-linux32{tag}', 'bztar'),
            'x86_64':   ('{package}-{version}-linux64{tag}', 'bztar'),
            'mingw32':  ('{package}-{version}-windows32{tag}', 'zip'),
            'mingw64':  ('{package}-{version}-windows64{tag}', 'zip'),
            }

    def __init__(self):
        src = make_source_code('latbuilder')
        aname, afmt = LatbuilderRules.ARCHIVE[BuildRules.TARGET]
        super().__init__(make_source_code('latbuilder'), aname, afmt)
        self.version = None
        self.tcode = None
        self._installed = False

    @property
    def b2_command(self):
        return [os.path.join(self.prefix, 'bin', 'b2'),
                '-j{}'.format(self.num_processes),
                '--prefix={}'.format(self.build_dir),
                'link={}'.format(LatbuilderRules.LINK),
                'tcode={}'.format(self.tcode),
                ]

    #def _dependencies(self):
    #    return []

    def _guess_local_gcc_version(self):
        return run_command(['gcc', '-dumpversion']).decode().strip()

    def _do_configure(self, log):
        with working_directory(self.source_dir):
            out = run_command([
                'git',
                'describe',
                '--tags',
                '--match=v[0-9]*'],
                log)
            self.version = out.decode().strip()[1:]
            out = run_command([
                os.path.join(self.prefix, 'bin', 'b2'),
                '-a',
                'toolset=gcc-{}'.format(self._guess_local_gcc_version()),
                'target-os={}'.format(platform.system().lower()),
                'address-model={}'.format(platform.machine() == 'x86_64' and 64 or 32),
                '/tools//tcode',
                ],
                log)
            for line in reversed(out.decode().split('\n')):
                m = re.match(r'^common\.copy\s+(.*)', line)
                if m:
                    self.tcode = m.group(1)
        self.archive_name = self.archive_name.format(
                package=self.package,
                version=self.version,
                tag='')
        logging.info('  current version: {}'.format(self.version))
        logging.info('  tcode path: {}'.format(self.tcode))
        logging.info('  archive name: {}'.format(self.archive_name))

    def _do_build(self, log):
        # latbuilder web interface
        if shutil.which('pyjsbuild'):
            logging.info("  building Lattice Builder Web Interface")
            bindir = os.path.join(self.build_dir, 'bin')
            websrc = os.path.join(self.source_dir, 'latbuilder-web')
            sharedir = os.path.join(self.build_dir, 'share')
            shutil.rmtree(bindir, ignore_errors=True)
            shutil.rmtree(sharedir, ignore_errors=True)
            shutil.copytree(os.path.join(websrc, 'bin'), bindir)
            os.makedirs(sharedir, exist_ok=True)
            with working_directory(self.build_dir):
                run_command(['pyjsbuild',
                    '--no-compile-inplace',
                    '--output=share/latbuilder-web',
                    '-I', websrc,
                    'LatBuilderWeb'], log)
        else:
            logging.warning("  pyjsbuild executable cannot be found; skipping "
            "installation of the Lattice Builder web interface")
        # latbuilder documentation
        if shutil.which('doxygen'):
            logging.info("  building Lattice Builder documentation")
            with working_directory(os.path.join(self.source_dir, 'doc')):
                run_command('doxygen', log)
        else:
            logging.warning("  doxygen executable cannot be found; skipping "
            "installation of the Lattice Builder documentation")
        logging.info("  building Lattice Builder executable program")
        # latbuilder executable
        with working_directory(self.source_dir):
            run_command(self.b2_command + ['/latbuilder//install'], log)

    def _do_install(self, log):
        bindir = os.path.join(self.build_dir, 'bin')
        libdir = os.path.join(self.build_dir, 'lib')
        pending = True
        while pending:
            pending = False
            dlls = set()
            for objfile in find_files(self.build_dir, r'\.(exe|dll)$'):
                with environment(LANG='C'):
                    out = run_command(['objdump', '-p', objfile])
                for line in out.decode().split('\n'):
                    m = re.match(r'^\s*DLL Name:\s*(.*)', line, re.IGNORECASE)
                    if m: dlls.add(m.group(1))
            dlls = [f for f in dlls if not re.match(
                r'^(KERNEL.*\.dll|USER.*\.dll|^msvcrt.*\.dll)',
                f, re.IGNORECASE)]
            if dlls:
                raise NotImplementedError("copying of DLL's not implemented")

            #for dll in dlls:
            #    if not os.path.exists(os.path.join(bindir, dll)) \
            #            and not os.path.exists(os.path.join(libdir, dll)):
            #        pass # FIXME
                        
            #	if [[ ! -f $prefix/bin/$dll && ! -f $prefix/lib/$dll ]]
            #	then
            #		source=$(find "$MINGW64_HOME" -name "$dll" | grep -v /debug/ || echo)
            #		if [[ -f "$source" ]]
            #		then
            #			cp "$source" "$prefix/bin"
            #			echo "intalling $dll"
            #			update_deps=1
            #		else
            #			echo "skipping $dll"
            #		fi
            #	fi

            self._installed = True

    def _check_configured(self):
        return self.version and self.tcode

    def _check_built(self):
        return os.path.exists(os.path.join(self.build_dir, 'bin', 'latbuilder')) \
            or os.path.exists(os.path.join(self.build_dir, 'bin', 'latbuilder.exe'))

    def _check_installed(self):
        # FIXME: check for dependencies
        return self._installed


##############################################################################
# Global Functions
##############################################################################

def parse_command_line():
    parser = argparse.ArgumentParser(
            description='Setup a build environment.')
    parser.add_argument(
            "-p", "--prefix",
            required=True,
            help="directory in which to install the build environment")
    parser.add_argument(
            "packages",
            choices=['gcc', 'fftw', 'b2', 'boost', 'latbuilder'],
            nargs='+',
            help="directory in which to install the build environment")
    parser.add_argument(
            "-t", "--target",
            choices=['i686', 'x86_64', 'mingw32', 'mingw64'],
            help="environment type",
            default=platform.machine())
    parser.add_argument(
            "-r", "--root",
            help="root working directory where to store sources and build files",
            default='.')
    parser.add_argument(
            "-j", "--processes",
            help="number of CPU's to use",
            default=cpu_count())
    return parser.parse_args()

def dump_state(state):
    for k, v in sorted(state.items()):
        print('  {:20s}: {}'.format(k, v))

##############################################################################
# Main
##############################################################################

if __name__ == '__main__':

    logging.basicConfig(
            level=logging.DEBUG,
            format='%(levelname)-8s %(message)s')
    args = parse_command_line()

    # persistent state
    statefile = os.path.join(args.root, 'sources.db'.format(args.target))
    persistent_state = shelve.open(statefile)

    # clean up state at exit
    import atexit
    atexit.register(lambda: persistent_state.close())

    # show current state
    #if persistent_state:
    #    print('Last state:')
    #    dump_state(persistent_state)

    # ensure prefix is an absolute path
    if not os.path.isabs(args.prefix):
        args.prefix = os.path.join(os.getcwd(), args.prefix)

    # set static variables
    SourceCode.STATE = persistent_state
    BuildRules.STATE = persistent_state
    SourceCode.ROOT = os.path.join(args.root, 'src')
    BuildRules.ROOT = os.path.join(args.root, '{}-build'.format(args.target))
    BuildRules.NUM_PROCESSES = args.processes
    BuildRules.PREFIX = args.prefix
    BuildRules.TARGET = args.target

    def create_rules(target, package):
        RulesClass = eval(package.capitalize() + 'Rules')
        if package == 'gcc':
            raise NotImplementedError('gcc installation not implemented')
        return RulesClass()

    for package in args.packages:
        rules = create_rules(args.target, package)
        if isinstance(rules, PackageRules):
            if not rules.packed:
                rules.pack()
        else:
            if not rules.installed:
                rules.install()

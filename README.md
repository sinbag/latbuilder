# Lattice Builder
_A general software tool for constructing rank-1 lattice rules_

*Lattice rules* are often used as a replacement for [Monte
Carlo](http://en.wikipedia.org/wiki/Monte_Carlo_integration) to integrate
multidimensional functions.
For certain problems, well-constructed lattice rules can dramatically reduce the integration error with respect to Monte Carlo.

Lattice Builder is a software tool and library that implements a variety of
construction algorithms for good rank-1 lattice rules.
It supports exhaustive and random searches, as well as component-by-component
(CBC) and random CBC constructions, for any number of points, and for various
measures of (non)uniformity of the points.
The implemented measures include the weighted P<sub>α</sub> square discrepancy,
the R<sub>α</sub> criterion, and figures of merit based on the spectral test,
with projection-dependent weights.
For numbers of points that are integer powers of a prime base, the construction
of embedded rank-1 lattice rules is supported through any of the above
algorithms, and also through a fast CBC algorithm, with a variety of
possibilities for the normalization of the merit values of individual embedded
levels and for their combination into a single merit value.

Details about lattice rules and Lattice Builder can be found in
[*Lattice Builder*: A General Software Tool for Constructing Rank-1 Latice Rules](http://www.iro.umontreal.ca/~lecuyer/myftp/papers/latbuilder.pdf).


## Quick Start Guide

The quickest way to get started Lattice Builder is to [download a binary distribution](https://drive.google.com/folderview?id=0B_lX__trikOgQ0kweFd0cHNGLTA&usp=sharing#list) pre-compiled for your platform (32/64-bit Linux/Windows):

* If you use 64-bit Windows, click on `latbuilder-X.Y.Z-windows64.zip`, then click on the *download* arrow in the bottom right corner of the screen
* If you use 32-bit Windows, click on `latbuilder-X.Y.Z-windows32.zip`, then click on the *download* arrow in the bottom right corner of the screen
* If you use 64-bit Linux, click on `latbuilder-X.Y.Z-linux64.tar.bz2`
* If you use 32-bit Linux, click on `latbuilder-X.Y.Z-linux32.tar.bz2`

where `X.Y.Z` is the latest Lattice Builder version.
Then, **simply unpack the archive; no further installation is required**.
The executable programs — the Lattice Builder command-line and web interfaces — can be found in the `latbuilder/bin` subdirectory.

You can then use the [Lattice Builder Web
Interface](https://googledrive.com/host/0B_lX__trikOgaGpYTXhEaHFMSmM/webif.html)
by installing [Python 2.7](http://python.org/download/) and executing the script

	latbuilder/bin/LatBuilderWeb.py

extracted from the binary package.

![Screenshot](doc/screenshots/latbuilder-web-1.png "Screenshot")

Or, you can read the [Lattice Builder Command Line Tutorial](https://googledrive.com/host/0B_lX__trikOgaGpYTXhEaHFMSmM/cmdtut.html) to teach yourself how to use the executable program extracted from the binary package at

	latbuilder/bin/latbuilder

for Linux distributions, or at

	latbuilder/bin/latbuilder.exe

for Windows distributions.


The structure of the binary packages is described in more detail in the
[Downloading Binaries](#downloading-binaries) section.

You can also choose to [compile it from source](#compiling-from-source).


## Downloading Binaries

The easiest way to start using Lattice Builder is to [download a binary
distribution](https://drive.google.com/folderview?id=0B_lX__trikOgQ0kweFd0cHNGLTA&usp=sharing#list) of Lattice
Builder, that includes the executable `latbuilder` program, together with
the Lattice Builder library and documentation.

The binary distribution packages have the following directory structure:

* **bin**: contains the executable `labuilder` program;
* **include**: contains the C++ header files necessary to use the Lattice
  Builder library;
* **lib**: contains the binary Lattice Builder library;
* **share/doc/latbuilder/html**: contains the HTML documentation;
* **share/doc/latbuilder/examples**: contains examples on using the Lattice
  Builder library;

The binary packages do not include an installation program.  To use the Lattice
Builder program, simply unpack the binary distribution package and move to its
root directory, then, e.g., to construct, component-by-component, a rank-1
lattice rule with 8191 points in 5 dimensions using the P-alpha criterion with
alpha=2 and with uniform product weights with value 0.1, issue the following
command on Linux:

	bin/latbuilder -l ordinary -n 8191 -d 5 -m CS:sum:P2 -w product:0.1 -c CBC

or, on Window systems:

	bin\latbuilder -l ordinary -n 8191 -d 5 -m CS:sum:P2 -w product:0.1 -c CBC

Try `bin/latbuilder --help` or read **share/doc/latbuilder/html/cmdtut.html**
for more information on using the Lattice Builder program.


## Compiling From Source

### Requirements

The following software must be installed in order to compile Lattice Builder:

* [Git](http://git-scm.com/)
* [C++11](http://www.iso.org/iso/iso_catalogue/catalogue_tc/catalogue_detail.htm?csnumber=50372)-Compliant Compiler (e.g., [GCC](http://gcc.gnu.org) 4.7)
* [Boost C++ Libraries](http://www.boost.org/)
* [FFTW Library](http://www.fftw.org/)
* [Boost.Build](http://www.boost.org/boost-build2/) (nightly build recommended)


### Configuring Boost.Build

Boost.Build needs to be told where to find the Boost and FFTW headers and how to
link to these libraries, via the `site-config.jam` configuration that can be
found under the directory `<b2-prefix>/share/boost-build`, where `<b2-prefix>`
is the prefix under which Boost.Build is installed.  If all libraries are
installed under standard paths, you can put the following contents into the
`site-config.jam` file:

	project site-config ;

	using gcc ;

	alias boost ; # header-only

	lib boost_program_options boost_system fftw3 ;
	lib boost_chrono : boost_system rt : <name>boost_chrono ;
	lib rt : : <link>shared ; # forced shared linkage

Otherwise, customize the following contents to suit your system configuration,
by replacing the `/opt/fftw3` and `/opt/boost` prefixes with the proper paths:

	project site-config ;
	
	lib fftw3 : : : <search>/opt/fftw3/lib/ : <include>/opt/fftw3/include/ ;

	alias boost : : : : <include>/opt/boost/include/ ;
	
	lib boost_program_options boost_system : :
		: <search>/opt/boost/lib/ : <include>/opt/boost/include/ ;

	lib boost_chrono : boost_system rt : <name>boost_chrono
		: <search>/opt/boost/lib/ : <include>/opt/boost/include/ ;

	lib rt : : <link>shared ;

The compilation process generates intermediate files; Boost.Build can be told to
put them in the temporary directory `/tmp/b2` b changing the project line of the
`site-config.jam` file to:

	project site-config : build-dir /tmp/b2 ;

**Remark:** If you do not have sufficient permissions to modify
the ̀`site-config.jam` file, you can resort to creating a `user-config.jam` file
at the root of your home directory and by modifying this file instead of the
`site-config.jam` file.


### Downloading from GitHub

Clone the Lattice Builder repository with:

	git clone git://github.com/mungerd/latbuilder.git

Then, move to the root directory of the repository with:

	cd latbuilder


### Configuring the Compiler to Use the C++11 Standard

The appropriate compiler flags should set in the `project-config.jam` file,
which can be found at the root of the source distribution, in order to support
the C++11 standard.  For example, with GCC 4.7, one can set:

	project latsoft : requirements <cxxflags>"-std=c++11" ;


### Compiling Lattice Builder

Change the current directory to the root or the source distribution.
First, compile the auxiliary tools that are needed to generate part of the
source code in Lattice Builder, with:

	b2 /tools

Then, prepare a binary distribution of Lattice Builder with:

	b2 /latbuilder//install --prefix=<dist-prefix>

where `<dist-prefix>` must be replaced with the directory into which Lattice
Builder should be installed.  The above command installs the `latbuilder`
executable under the `<dist-prefix>/bin` directory.


## Using the Lattice Builder Program

If the compilation suceeded, the following command should output the installed 
version of Lattice Builder:

	<dist-prefix>/bin/latbuilder --version

Help on usage can also be obtained by using the `--help` switch.


## Using the Lattice Builder Web Interface

The Lattice Builder Web Interface is included in the binary packages.
[Python 2.7](http://python.org/download/) must be installed on the host machine.
The local web server can be started by launching the following Python script:

	<dist-prefix>/bin/LatBuilderWeb.py

The web interface can then be used by connecting a browser to the
[http://localhost:8080](http://localhost:8080/LatBuilderWeb.html).


## Using the Lattice Builder Library

An example Jamfile and an example Makefile that can be modified to build a
project that uses the Lattice Builder application programming interface (API)
can be found under the `<dist-prefix>/share/doc/examples/myproject` directory,
together with a very simple piece of code.

For more information and a tutorial, refer to the HTML documentation in the
`<dist-prefix>/share/doc/html` directory.


## Frequently Asked Questions

### What construction type should I use to find good high-dimensional lattices in reasonable time?

Fast CBC with a coordinate-symmetric figure of merit.

For example, the following command line performs a fast CBC construction using
the weighted P-alpha criterion with alpha=2 and with product weights giving
the same weight of 0.01 to every coordinate (this means a weight of 1e-2
for projections of order 1, of 1e-4 for projections of order 2, of 1e-6 for
projections of order 3, etc.):

	latbuilder -l ordinary -n 2^16 -d 100 -m CS:sum:P2 -c fast-CBC -w product:0.01

The above search is for n=2^16=65,536 points in dimension 100.  Lattice Builder
does that very quickly.


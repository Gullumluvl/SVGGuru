#!/usr/bin/env perl
use warnings ;
use strict ;

my $factor = pop(@ARGV) || 1;
#print $factor . "\n" ;

while (<>) {
	if ( m/(?<=font-size:)\d+(?=px)/ ) {
		my $fontsize = $& ;
		my $newfontsize = $fontsize * $factor ;
		#print $fontsize , $newfontsize . "\n" ;
		s/(?<=font-size:)\d+(?=px)/$newfontsize/ ;
	}
	print ;
}


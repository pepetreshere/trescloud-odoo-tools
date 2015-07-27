BEGIN {
    count = 0;
}
($1 " " substr($2, 0, 8)) > FECHA {
    count = count + 1;
}
END { print count; }
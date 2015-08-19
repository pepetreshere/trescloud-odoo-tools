BEGIN {
    count = 0;
}
{
    count = count + 1;
}
END { print count; }
BEGIN {
    sum=0; count=0; min=0;
}
{
    split($8, t, ":");
    time = 0 + t[2];
    sum += time;
    count += 1;
    min = (time > min) ? min : time
}
END { print min, (count > 0) ? (sum/count) : 0; }
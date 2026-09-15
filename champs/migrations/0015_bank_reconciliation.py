from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def set_payment_references(apps, schema_editor):
    Registration = apps.get_model('champs', 'Registration')
    for registration in Registration.objects.filter(payment_reference__isnull=True):
        registration.payment_reference = '5DB-C%s-R%s' % (registration.champ_id, registration.id)
        registration.save(update_fields=['payment_reference'])


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('champs', '0014_champcost_scope'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='payment_reference',
            field=models.CharField(blank=True, max_length=32, null=True, verbose_name='Referencia de transferencia'),
        ),
        migrations.RunPython(set_payment_references, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='registration',
            name='payment_reference',
            field=models.CharField(blank=True, max_length=32, null=True, unique=True, verbose_name='Referencia de transferencia'),
        ),
        migrations.CreateModel(
            name='BankTransaction',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('external_id', models.CharField(max_length=255, unique=True, verbose_name='Identificador bancario')),
                ('booking_date', models.DateField(verbose_name='Fecha contable')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Importe')),
                ('payer', models.CharField(blank=True, default='', max_length=255, verbose_name='Ordenante')),
                ('reference', models.CharField(blank=True, default='', max_length=255, verbose_name='Concepto')),
                ('imported_at', models.DateTimeField(auto_now_add=True)),
                ('imported_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='imported_bank_transactions', to=settings.AUTH_USER_MODEL)),
            ],
            options={'verbose_name': 'Movimiento bancario', 'verbose_name_plural': 'Movimientos bancarios', 'ordering': ['-booking_date', '-id']},
        ),
        migrations.CreateModel(
            name='PaymentAllocation',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.DecimalField(decimal_places=2, max_digits=10, verbose_name='Importe conciliado')),
                ('confirmed_at', models.DateTimeField(auto_now_add=True)),
                ('companion', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bank_allocations', to='champs.travelcompanion')),
                ('confirmed_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='confirmed_payment_allocations', to=settings.AUTH_USER_MODEL)),
                ('registration', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='bank_allocations', to='champs.registration')),
                ('transaction', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='allocations', to='champs.banktransaction')),
            ],
            options={'verbose_name': 'Imputación de pago', 'verbose_name_plural': 'Imputaciones de pago'},
        ),
    ]
